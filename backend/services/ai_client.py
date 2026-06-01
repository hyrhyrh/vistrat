"""v3.0 统一 AI 分析客户端（主+备 fallback）"""

import asyncio
import json
import logging
import os
import random
import re

import httpx

from config.settings import AIAnalysisConfig

logger = logging.getLogger(__name__)


ANALYSIS_PROMPT_SUFFIX = """
请以 JSON 格式返回分析结果：
```json
{
  "has_violation": true,
  "confidence": 0.85,
  "violations": [
    {"type": "类型代码", "description": "描述", "severity": "high", "count": 1}
  ],
  "scene_description": "场景描述"
}
```
仅返回 JSON，不要添加额外解释。"""


def parse_ai_response(response_text: str) -> dict:
    """多级 JSON 解析 AI 响应"""
    # 1. 直接解析
    try:
        return json.loads(response_text)
    except (json.JSONDecodeError, TypeError):
        pass

    # 2. 提取 ```json ... ``` 块
    match = re.search(r"```json\s*\n?(.*?)\n?\s*```", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # 3. 提取最外层 {}
    match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, TypeError):
            pass

    # 4. Fallback
    return {
        "has_violation": False,
        "confidence": 0.0,
        "violations": [],
        "scene_description": response_text[:500] if response_text else "",
        "parse_error": "无法解析 AI 响应为 JSON",
    }


class AIAnalysisClient:
    """统一 AI 分析客户端，支持主备 fallback 和指数退避重试"""

    def __init__(self):
        self.semaphore = asyncio.Semaphore(AIAnalysisConfig.MAX_AI_CONCURRENCY)
        self._client: httpx.AsyncClient | None = None
        self._primary_key = os.getenv(AIAnalysisConfig.PRIMARY_API_KEY_ENV, "")
        self._fallback_key = os.getenv(AIAnalysisConfig.FALLBACK_API_KEY_ENV, "")

    async def _ensure_client(self):
        """延迟初始化 httpx 客户端，复用连接池"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(AIAnalysisConfig.REQUEST_TIMEOUT)
            )

    async def analyze_frame(self, image_base64: str, prompt: str) -> dict:
        """分析单帧图像，主模型优先，失败自动 fallback 到备用模型"""
        async with self.semaphore:
            await self._ensure_client()

            # 主模型
            try:
                raw = await self._call_with_retry(
                    model=AIAnalysisConfig.PRIMARY_MODEL,
                    api_url=AIAnalysisConfig.PRIMARY_API_URL,
                    api_key=self._primary_key,
                    image_base64=image_base64,
                    prompt=prompt,
                )
                return parse_ai_response(raw)
            except Exception as primary_err:
                logger.warning(
                    "主模型调用失败，切换备用模型: %s", primary_err
                )

            # 备用模型
            try:
                raw = await self._call_with_retry(
                    model=AIAnalysisConfig.FALLBACK_MODEL,
                    api_url=AIAnalysisConfig.FALLBACK_API_URL,
                    api_key=self._fallback_key,
                    image_base64=image_base64,
                    prompt=prompt,
                )
                return parse_ai_response(raw)
            except Exception as fallback_err:
                logger.error("备用模型也失败: %s", fallback_err)
                raise

    async def _call_with_retry(
        self,
        model: str,
        api_url: str,
        api_key: str,
        image_base64: str,
        prompt: str,
        max_retries: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
    ) -> str:
        """带指数退避重试的 API 调用"""
        if max_retries is None:
            max_retries = AIAnalysisConfig.MAX_RETRIES
        if base_delay is None:
            base_delay = AIAnalysisConfig.RETRY_BASE_DELAY
        if max_delay is None:
            max_delay = AIAnalysisConfig.RETRY_MAX_DELAY

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                return await self._call_api(model, api_url, api_key, image_base64, prompt)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    logger.warning(
                        "AI 调用失败 (attempt %d/%d), %.1fs 后重试: %s",
                        attempt + 1, max_retries, delay + jitter, e,
                    )
                    await asyncio.sleep(delay + jitter)
        raise last_error  # type: ignore[misc]

    async def _call_api(
        self,
        model: str,
        api_url: str,
        api_key: str,
        image_base64: str,
        prompt: str,
    ) -> str:
        """发送 OpenAI 兼容格式的视觉分析请求"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        data = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                }
            ],
            "temperature": AIAnalysisConfig.TEMPERATURE,
            "max_tokens": AIAnalysisConfig.MAX_TOKENS,
        }

        response = await self._client.post(api_url, headers=headers, json=data)  # type: ignore[union-attr]
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]

    async def close(self):
        """关闭 httpx 客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
