"""
Vistrat 推理客户端单元测试
覆盖：正常解析、4xx 不重试、5xx 触发熔断、API Key 传递
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


# ---------------------------------------------------------------------------
# 固定响应样本（契约对齐）
# ---------------------------------------------------------------------------
SAMPLE_ANALYZE_RESPONSE = {
    "request_id": "trace-uuid-xyz",
    "vlm_result": {
        "has_violation": True,
        "violations": ["未戴安全帽"],
        "scene_description": "工地现场，1 名工人未戴安全帽",
        "raw_text": "{\"has_violation\": true}",
        "latency_ms": 2840,
        "error": None,
    },
    "detection_objects": [
        {
            "label": "worker without helmet",
            "confidence": 0.87,
            "bbox": {"x": 320, "y": 110, "width": 180, "height": 420},
            "severity": "high",
        }
    ],
    "image_size": {"width": 1920, "height": 1080},
    "total_latency_ms": 3120,
}

SAMPLE_TEMPLATE = {
    "id": "safety_helmet_v2",
    "name": "未戴安全帽检测",
    "provider": "qwen-vl-max",
    "system_prompt": "你是安全监察员",
    "user_prompt": "检查图中工人",
    "confidence_threshold": 0.35,
    "detection_capabilities": ["未戴安全帽"],
}


def _make_response(status_code: int, json_body=None, text_body: str = ""):
    """构造一个 httpx Response-like 对象"""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=json_body or {})
    resp.text = text_body or str(json_body or "")
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# 正常解析
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analyze_success_parses_response():
    from services.inference_client import InferenceClient

    client = InferenceClient()
    await client.startup()

    # mock storage 预签名
    with patch("services.inference_client.storage_service") as mock_storage:
        mock_storage.generate_presigned_get.return_value = (
            "https://minio.local/images/analysis/task1/frame_000001.jpg?sig=xxx"
        )
        # mock httpx 调用
        mock_post = AsyncMock(return_value=_make_response(200, SAMPLE_ANALYZE_RESPONSE))
        client._client.post = mock_post

        result = await client.analyze(
            image_minio_key="analysis/task1/frame_000001.jpg",
            template=SAMPLE_TEMPLATE,
            violations_hint=["未戴安全帽"],
            request_id="trace-uuid-xyz",
        )

    assert result.request_id == "trace-uuid-xyz"
    assert result.vlm_result.has_violation is True
    assert len(result.detection_objects) == 1
    assert result.detection_objects[0].confidence == 0.87
    assert result.detection_objects[0].bbox.x == 320
    assert result.total_latency_ms == 3120

    # 验证 POST 调用参数
    call_kwargs = mock_post.call_args
    sent_payload = call_kwargs.kwargs["json"]
    assert sent_payload["template_id"] == "safety_helmet_v2"
    assert "worker without helmet" in sent_payload["detect"]["text_prompt"]
    assert sent_payload["detect"]["enable"] is True
    assert sent_payload["vlm"]["provider"] == "qwen-vl-max"

    await client.shutdown()


# ---------------------------------------------------------------------------
# API Key header
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_key_header_is_set():
    from services.inference_client import InferenceClient
    from config.settings import InferenceConfig

    original_key = InferenceConfig.API_KEY
    InferenceConfig.API_KEY = "test-secret-key-123"
    try:
        client = InferenceClient()
        await client.startup()
        assert client._client.headers.get("X-Vistrat-API-Key") == "test-secret-key-123"
        await client.shutdown()
    finally:
        InferenceConfig.API_KEY = original_key


# ---------------------------------------------------------------------------
# 4xx 不重试
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_4xx_not_retried():
    from services.inference_client import InferenceClient, InferenceHTTPError

    client = InferenceClient()
    await client.startup()

    with patch("services.inference_client.storage_service") as mock_storage:
        mock_storage.generate_presigned_get.return_value = "http://minio/img.jpg"
        mock_post = AsyncMock(return_value=_make_response(400, {}, "bad template_id"))
        client._client.post = mock_post

        with pytest.raises(InferenceHTTPError):
            await client.analyze(
                image_minio_key="x.jpg",
                template=SAMPLE_TEMPLATE,
                violations_hint=[],
            )

        # 只调用 1 次，不重试
        assert mock_post.call_count == 1

    await client.shutdown()


# ---------------------------------------------------------------------------
# 5xx 连续失败触发熔断
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_5xx_triggers_circuit_breaker():
    from services.inference_client import InferenceClient, InferenceUnavailable
    from config.settings import InferenceConfig

    client = InferenceClient()
    # 改小阈值和重试次数，加速测试
    client._breaker._threshold = 3
    original_retries = InferenceConfig.MAX_RETRIES
    InferenceConfig.MAX_RETRIES = 0  # 不重试，单次即失败
    try:
        await client.startup()

        with patch("services.inference_client.storage_service") as mock_storage, \
             patch("services.inference_client.asyncio.sleep", new=AsyncMock()):
            mock_storage.generate_presigned_get.return_value = "http://minio/img.jpg"
            mock_post = AsyncMock(return_value=_make_response(500, {}, "boom"))
            client._client.post = mock_post

            # 连续 3 次 500 → 触发熔断
            for _ in range(3):
                with pytest.raises(InferenceUnavailable):
                    await client.analyze(
                        image_minio_key="x.jpg",
                        template=SAMPLE_TEMPLATE,
                        violations_hint=[],
                    )

            # 下一次调用应直接熔断，不打 HTTP
            call_count_before = mock_post.call_count
            with pytest.raises(InferenceUnavailable) as excinfo:
                await client.analyze(
                    image_minio_key="x.jpg",
                    template=SAMPLE_TEMPLATE,
                    violations_hint=[],
                )
            assert "熔断" in str(excinfo.value)
            assert mock_post.call_count == call_count_before  # 未发 HTTP

        await client.shutdown()
    finally:
        InferenceConfig.MAX_RETRIES = original_retries


# ---------------------------------------------------------------------------
# text_prompt 中英映射
# ---------------------------------------------------------------------------
def test_build_text_prompt_maps_chinese_to_english():
    from services.inference_client import build_text_prompt

    prompt = build_text_prompt(["未戴安全帽", "抽烟"])
    assert "worker without helmet" in prompt
    assert "smoking" in prompt


def test_build_text_prompt_empty():
    from services.inference_client import build_text_prompt
    assert build_text_prompt([]) == ""
