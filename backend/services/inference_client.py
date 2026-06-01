"""
Vistrat A100 推理服务客户端
主后端（CPU 服务器）通过 HTTP 调用中台 A100 推理服务完成 VLM + DINO 检测
"""

import asyncio
import logging
import random
import time
import uuid
from collections import deque
from typing import Any, Dict, List, Optional

import httpx

from config.settings import InferenceConfig, StorageConfig
from models.inference import InferenceResult
from services.storage import storage_service

logger = logging.getLogger(__name__)


# ==================== 中英 violation 映射表 ====================
# 主后端自带简版映射：违规中文名 → DINO text_prompt 英文片段
# 与 vistrat-inference/app/services/prompt_builder.py 保持一致
VIOLATION_EN_MAP: Dict[str, str] = {
    "未戴安全帽": "worker without helmet. bare head.",
    "未佩戴安全帽": "worker without helmet. bare head.",
    "未穿反光背心": "worker without reflective vest. person not wearing safety vest.",
    "未穿反光衣": "worker without reflective vest. person not wearing safety vest.",
    "抽烟": "person smoking. cigarette in mouth.",
    "吸烟": "person smoking. cigarette in mouth.",
    "打手机": "person using phone. holding mobile phone.",
    "玩手机": "person using phone. holding mobile phone.",
    "高空无安全带": "worker at height without safety harness.",
    "未系安全带": "worker at height without safety harness.",
    "区域入侵": "person in restricted area. intruder.",
    "人员入侵": "person in restricted area. intruder.",
}


def build_text_prompt(violations_hint: List[str]) -> str:
    """
    根据 violation 中文名列表构建 DINO text_prompt

    DINO 的 text_prompt 规范：英文短语，句点分隔。
    未命中映射的保留中文（A100 端的 prompt_builder 会兜底处理）。
    """
    if not violations_hint:
        return ""
    parts: List[str] = []
    for name in violations_hint:
        en = VIOLATION_EN_MAP.get(name)
        if en:
            parts.append(en)
        else:
            # 兜底：直接拼中文，A100 那边有完整映射表
            parts.append(name)
    return " ".join(parts)


# ==================== 异常 ====================
class InferenceUnavailable(Exception):
    """推理服务不可用（熔断或重试耗尽）"""


class InferenceHTTPError(Exception):
    """4xx 错误，不可重试"""


# ==================== 熔断器 ====================
class _CircuitBreaker:
    """
    简易熔断器：time-window 内失败数 >= 阈值 → 开启熔断 cooldown 秒
    """

    def __init__(self, window: int, threshold: int, cooldown: int):
        self._window = window
        self._threshold = threshold
        self._cooldown = cooldown
        self._failures: deque = deque()  # 存 timestamp
        self._open_until: float = 0.0
        self._lock = asyncio.Lock()

    async def is_open(self) -> bool:
        async with self._lock:
            return time.time() < self._open_until

    async def record_success(self) -> None:
        async with self._lock:
            self._failures.clear()

    async def record_failure(self) -> None:
        async with self._lock:
            now = time.time()
            self._failures.append(now)
            # 移除窗口外的失败
            cutoff = now - self._window
            while self._failures and self._failures[0] < cutoff:
                self._failures.popleft()
            if len(self._failures) >= self._threshold:
                self._open_until = now + self._cooldown
                self._failures.clear()
                logger.error(
                    f"⚠️ 推理服务熔断已开启（{self._threshold} 次失败/{self._window}s），"
                    f"冷却 {self._cooldown}s"
                )


# ==================== 客户端 ====================
class InferenceClient:
    """A100 推理服务 HTTP 客户端"""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None
        self._breaker = _CircuitBreaker(
            window=InferenceConfig.BREAKER_WINDOW_SECONDS,
            threshold=InferenceConfig.BREAKER_FAIL_THRESHOLD,
            cooldown=InferenceConfig.BREAKER_COOLDOWN_SECONDS,
        )

    async def startup(self) -> None:
        """lifespan 启动钩子：构造 AsyncClient"""
        if self._client is None:
            headers = {"X-Vistrat-API-Key": InferenceConfig.API_KEY} if InferenceConfig.API_KEY else {}
            self._client = httpx.AsyncClient(
                base_url=InferenceConfig.BASE_URL,
                timeout=InferenceConfig.TIMEOUT,
                headers=headers,
            )
            logger.info(f"✅ InferenceClient 已初始化: {InferenceConfig.BASE_URL}")

    async def shutdown(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("✅ InferenceClient 已关闭")

    async def analyze(
        self,
        image_minio_key: str,
        template: Dict[str, Any],
        violations_hint: List[str],
        request_id: Optional[str] = None,
        bucket: Optional[str] = None,
    ) -> InferenceResult:
        """
        调用 A100 /v1/analyze 完成 VLM + DINO 检测

        Args:
            image_minio_key: MinIO 对象键（不含 bucket）
            template: 算法模板 dict，需含 provider/model_name/system_prompt/user_prompt
            violations_hint: 违规类型中文名列表，用于生成 DINO text_prompt
            request_id: 追踪 ID；不传自动生成
            bucket: MinIO 桶名，默认用 ANNOTATION_BUCKET 下的分析帧桶（images）

        Returns:
            InferenceResult

        Raises:
            InferenceUnavailable: 熔断开启 / 重试耗尽
            InferenceHTTPError: 4xx（不可重试）
        """
        if not InferenceConfig.ENABLED:
            raise InferenceUnavailable("INFERENCE_ENABLED=false")

        if await self._breaker.is_open():
            raise InferenceUnavailable("推理服务熔断中，跳过真实 HTTP 调用")

        if self._client is None:
            # 懒启动兜底（比如单测或脚本环境）
            await self.startup()

        req_id = request_id or str(uuid.uuid4())
        # 帧图片默认桶：与 storage.upload_frame_image 保持一致（"images"）
        image_bucket = bucket or "images"

        # 1. 生成预签名 URL
        try:
            image_url = storage_service.generate_presigned_get(
                image_bucket,
                image_minio_key,
                expires=InferenceConfig.PRESIGNED_EXPIRES_SECONDS,
            )
        except Exception as e:
            logger.error(f"[{req_id}] 预签名失败: {e}")
            raise InferenceUnavailable(f"生成预签名URL失败: {e}") from e

        # 2. 构造 payload
        text_prompt = build_text_prompt(violations_hint)
        payload: Dict[str, Any] = {
            "image_url": image_url,
            "template_id": str(template.get("id", "")),
            "vlm": {
                "provider": template.get("provider") or template.get("model_name") or "qwen-vl-max",
                "system_prompt": template.get("system_prompt", ""),
                "user_prompt": template.get("user_prompt", ""),
            },
            "detect": {
                "enable": bool(text_prompt),
                "text_prompt": text_prompt,
                "threshold": float(template.get("confidence_threshold", 0.35) or 0.35),
            },
            "request_id": req_id,
        }

        # 3. 带重试的 POST
        return await self._post_with_retry("/v1/analyze", payload, req_id)

    async def _post_with_retry(
        self, path: str, payload: Dict[str, Any], req_id: str
    ) -> InferenceResult:
        assert self._client is not None
        last_exc: Optional[Exception] = None

        for attempt in range(InferenceConfig.MAX_RETRIES + 1):
            try:
                resp = await self._client.post(path, json=payload)

                # 4xx 不重试
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    await self._breaker.record_failure()
                    logger.error(
                        f"[{req_id}] 推理服务 4xx: {resp.status_code} {resp.text[:300]}"
                    )
                    raise InferenceHTTPError(
                        f"推理服务 {resp.status_code}: {resp.text[:200]}"
                    )

                # 429 / 5xx 可重试
                if resp.status_code == 429 or resp.status_code >= 500:
                    last_exc = InferenceUnavailable(
                        f"推理服务 {resp.status_code}: {resp.text[:200]}"
                    )
                    await self._breaker.record_failure()
                    if attempt < InferenceConfig.MAX_RETRIES:
                        await asyncio.sleep(self._backoff(attempt))
                        continue
                    raise last_exc

                # 2xx
                resp.raise_for_status()
                data = resp.json()
                await self._breaker.record_success()
                return InferenceResult.model_validate(data)

            except InferenceHTTPError:
                raise
            except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as e:
                last_exc = e
                await self._breaker.record_failure()
                logger.warning(
                    f"[{req_id}] 推理服务网络错误 attempt={attempt}: {e}"
                )
                if attempt < InferenceConfig.MAX_RETRIES:
                    await asyncio.sleep(self._backoff(attempt))
                    continue
                raise InferenceUnavailable(f"推理服务网络错误: {e}") from e
            except Exception as e:
                # 包括 JSON 解析 / pydantic 校验失败
                last_exc = e
                await self._breaker.record_failure()
                logger.error(f"[{req_id}] 推理服务响应解析失败: {e}")
                raise InferenceUnavailable(f"推理服务响应异常: {e}") from e

        # 理论上不会走到
        raise InferenceUnavailable(f"推理服务重试耗尽: {last_exc}")

    @staticmethod
    def _backoff(attempt: int) -> float:
        """指数退避 + 抖动：0.5 * 2^attempt + [0, 0.3]"""
        return 0.5 * (2 ** attempt) + random.uniform(0.0, 0.3)


# ==================== 单例 ====================
inference_client = InferenceClient()
