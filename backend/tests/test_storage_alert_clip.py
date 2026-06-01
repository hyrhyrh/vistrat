"""StorageService.upload_alert_clip 单元测试"""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from services.storage import StorageService


@pytest.mark.asyncio
async def test_upload_alert_clip_success(tmp_path: Path):
    """成功路径：验证调用 minio_client.upload_file 时传入正确的 bucket/key/content-type。"""
    mp4 = tmp_path / "alert-xyz.mp4"
    mp4.write_bytes(b"\x00" * 256)

    svc = StorageService()
    upload_file_mock = AsyncMock()
    svc.minio_client.upload_file = upload_file_mock  # type: ignore

    with patch(
        "services.storage.StorageService.convert_to_proxy_url",
        return_value="/api/image-proxy/minio/alert-clips/alert-xyz.mp4",
    ):
        url = await svc.upload_alert_clip(alert_id="alert-xyz", local_mp4_path=str(mp4))

    assert url == "/api/image-proxy/minio/alert-clips/alert-xyz.mp4"

    upload_file_mock.assert_awaited_once()
    kwargs = upload_file_mock.call_args.kwargs
    assert kwargs["bucket_name"] == "alert-clips"
    assert kwargs["object_key"] == "alert-xyz.mp4"
    assert kwargs["content_type"] == "video/mp4"
    assert kwargs["metadata"]["alert_id"] == "alert-xyz"
    assert kwargs["metadata"]["data_type"] == "alert_clip"
    # 文件内容按字节传入
    assert kwargs["file_content"] == b"\x00" * 256


@pytest.mark.asyncio
async def test_upload_alert_clip_file_missing():
    """本地文件不存在 → 抛异常（由调用方 ClipService 顶层捕获）。"""
    svc = StorageService()
    with pytest.raises(Exception):
        await svc.upload_alert_clip(
            alert_id="missing", local_mp4_path="/tmp/does_not_exist_xyz.mp4"
        )


@pytest.mark.asyncio
async def test_upload_alert_clip_minio_error_propagates(tmp_path: Path):
    """MinIO 调用抛异常向上传播（ClipService 层负责兜底）。"""
    mp4 = tmp_path / "bad.mp4"
    mp4.write_bytes(b"x")

    svc = StorageService()
    svc.minio_client.upload_file = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore

    with pytest.raises(RuntimeError, match="boom"):
        await svc.upload_alert_clip(alert_id="bad", local_mp4_path=str(mp4))
