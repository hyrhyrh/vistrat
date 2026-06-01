"""ClipService 单元测试

覆盖：
    - segment 筛选窗口边界（跨 segment 起点/终点）
    - ffmpeg 参数正确性（concat + -c copy + +faststart）
    - 非零退出码失败兜底
    - 空窗口兜底
    - MinIO 上传失败兜底
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 确保 sys.path 包含 backend（由 conftest.py 处理）
from services.clip_service import ClipService  # noqa: E402
from services.mediamtx_client import RecordingSegment  # noqa: E402


def _make_segment(tmp_path: Path, stream_id: str, ts: datetime) -> Path:
    """在 tmp_path/stream_id/ 下创建一个 fake segment 文件，文件名按 mediamtx 格式。"""
    stream_dir = tmp_path / stream_id
    stream_dir.mkdir(parents=True, exist_ok=True)
    # 格式: %Y-%m-%d_%H-%M-%S-%f（6位微秒）
    name = ts.strftime("%Y-%m-%d_%H-%M-%S-") + f"{ts.microsecond:06d}.mp4"
    p = stream_dir / name
    p.write_bytes(b"\x00\x00\x00\x20ftypmp42")  # 假的 mp4 header，非空即可
    return p


# ---------------------------------------------------------------------------
# list_recording_segments 边界测试（直接测试 MediaMTXClient 方法）
# ---------------------------------------------------------------------------

def test_list_segments_window_covers_boundary(tmp_path: Path):
    """窗口起点落在某 segment 中间时，该 segment 必须被包含。"""
    from services.mediamtx_client import MediaMTXClient

    base = datetime(2026, 4, 19, 10, 30, 0)
    # 三个 10s 段：[0, 10), [10, 20), [20, 30)
    _make_segment(tmp_path, "cam01", base)
    _make_segment(tmp_path, "cam01", base.replace(second=10))
    _make_segment(tmp_path, "cam01", base.replace(second=20))

    # 窗口 [10:30:05, 10:30:15] 横跨 seg0 和 seg1
    window_start = base.replace(second=5)
    window_end = base.replace(second=15)

    segments = MediaMTXClient.list_recording_segments(
        stream_id="cam01",
        window_start=window_start,
        window_end=window_end,
        recording_root=str(tmp_path),
        segment_duration_seconds=10,
    )

    assert len(segments) == 2
    # 按 start_ts 升序
    assert segments[0].start_ts == base
    assert segments[1].start_ts == base.replace(second=10)


def test_list_segments_empty_on_missing_dir(tmp_path: Path):
    from services.mediamtx_client import MediaMTXClient

    segments = MediaMTXClient.list_recording_segments(
        stream_id="nonexistent",
        window_start=datetime(2026, 4, 19, 10, 0, 0),
        window_end=datetime(2026, 4, 19, 10, 1, 0),
        recording_root=str(tmp_path),
    )
    assert segments == []


def test_list_segments_no_match(tmp_path: Path):
    """窗口完全在所有 segment 之外，返回空。"""
    from services.mediamtx_client import MediaMTXClient

    _make_segment(tmp_path, "cam01", datetime(2026, 4, 19, 10, 30, 0))
    # 窗口在前一天
    segments = MediaMTXClient.list_recording_segments(
        stream_id="cam01",
        window_start=datetime(2026, 4, 18, 10, 0, 0),
        window_end=datetime(2026, 4, 18, 10, 1, 0),
        recording_root=str(tmp_path),
    )
    assert segments == []


def test_list_segments_ignores_malformed_names(tmp_path: Path):
    """文件名不符合 %Y-%m-%d_%H-%M-%S-%f 的忽略。"""
    from services.mediamtx_client import MediaMTXClient

    stream_dir = tmp_path / "cam01"
    stream_dir.mkdir()
    (stream_dir / "garbage.mp4").write_bytes(b"x")
    (stream_dir / "2026-04-19.mp4").write_bytes(b"x")  # 不完整
    good = _make_segment(tmp_path, "cam01", datetime(2026, 4, 19, 10, 30, 0))

    segments = MediaMTXClient.list_recording_segments(
        stream_id="cam01",
        window_start=datetime(2026, 4, 19, 10, 29, 0),
        window_end=datetime(2026, 4, 19, 10, 31, 0),
        recording_root=str(tmp_path),
    )
    assert len(segments) == 1
    assert segments[0].path == good


# ---------------------------------------------------------------------------
# ClipService.create_alert_clip 集成测试
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_clip_empty_window_returns_none(tmp_path: Path):
    """扫描不到 segment 时返回 None，不抛异常。"""
    svc = ClipService(recording_root=str(tmp_path))
    result = await svc.create_alert_clip(
        alert_id="alert-1",
        stream_id="cam01",
        trigger_ts=datetime(2026, 4, 19, 10, 30, 0),
    )
    assert result is None


@pytest.mark.asyncio
async def test_create_clip_ffmpeg_nonzero_returns_none(tmp_path: Path):
    """ffmpeg 非零退出 → 返回 None，不抛。"""
    _make_segment(tmp_path, "cam01", datetime(2026, 4, 19, 10, 30, 0))
    svc = ClipService(recording_root=str(tmp_path))

    # mock asyncio.create_subprocess_exec 模拟 ffmpeg 失败
    fake_proc = MagicMock()
    fake_proc.returncode = 1
    fake_proc.communicate = AsyncMock(return_value=(b"", b"fake ffmpeg error"))

    with patch(
        "services.clip_service.asyncio.create_subprocess_exec",
        new=AsyncMock(return_value=fake_proc),
    ):
        result = await svc.create_alert_clip(
            alert_id="alert-2",
            stream_id="cam01",
            trigger_ts=datetime(2026, 4, 19, 10, 30, 5),
        )
    assert result is None


@pytest.mark.asyncio
async def test_create_clip_success_calls_ffmpeg_and_uploads(tmp_path: Path):
    """成功路径：验证 ffmpeg 参数正确、MinIO 上传被调用、返回 URL。"""
    ts = datetime(2026, 4, 19, 10, 30, 0)
    _make_segment(tmp_path, "cam01", ts)
    _make_segment(tmp_path, "cam01", ts.replace(second=10))

    svc = ClipService(recording_root=str(tmp_path))
    captured_args = {}

    async def fake_exec(*args, **kwargs):
        captured_args["args"] = list(args)
        # 模拟 ffmpeg 成功，并真实创建非空 output 文件
        # args 最后一个是 output path
        out = Path(args[-1])
        out.write_bytes(b"\x00\x00\x00\x20ftypmp42" + b"x" * 100)
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))
        return proc

    upload_mock = AsyncMock(return_value="/api/image-proxy/minio/alert-clips/alert-3.mp4")

    with patch(
        "services.clip_service.asyncio.create_subprocess_exec",
        new=fake_exec,
    ), patch(
        "services.clip_service.storage_service.upload_alert_clip",
        new=upload_mock,
    ):
        result = await svc.create_alert_clip(
            alert_id="alert-3",
            stream_id="cam01",
            trigger_ts=ts.replace(second=5),
            pre_seconds=5,
            post_seconds=10,
        )

    assert result == "/api/image-proxy/minio/alert-clips/alert-3.mp4"
    upload_mock.assert_awaited_once()

    # 校验 ffmpeg 参数
    args = captured_args["args"]
    assert "-f" in args and "concat" in args
    assert "-safe" in args and "0" in args
    assert "-c" in args and "copy" in args
    assert "-movflags" in args and "+faststart" in args
    # 最后一个参数是输出 mp4
    assert args[-1].endswith(".mp4")


@pytest.mark.asyncio
async def test_create_clip_upload_failure_returns_none(tmp_path: Path):
    """MinIO 上传抛异常 → 返回 None，不传播。"""
    ts = datetime(2026, 4, 19, 10, 30, 0)
    _make_segment(tmp_path, "cam01", ts)
    svc = ClipService(recording_root=str(tmp_path))

    async def fake_exec(*args, **kwargs):
        out = Path(args[-1])
        out.write_bytes(b"x" * 100)
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))
        return proc

    with patch(
        "services.clip_service.asyncio.create_subprocess_exec",
        new=fake_exec,
    ), patch(
        "services.clip_service.storage_service.upload_alert_clip",
        new=AsyncMock(side_effect=RuntimeError("minio down")),
    ):
        result = await svc.create_alert_clip(
            alert_id="alert-4",
            stream_id="cam01",
            trigger_ts=ts.replace(second=5),
        )
    assert result is None


@pytest.mark.asyncio
async def test_create_clip_concat_list_content(tmp_path: Path):
    """验证 concat.txt 内容按时间顺序排列，每行 file '<path>'。"""
    ts = datetime(2026, 4, 19, 10, 30, 0)
    seg0 = _make_segment(tmp_path, "cam01", ts)
    seg1 = _make_segment(tmp_path, "cam01", ts.replace(second=10))

    svc = ClipService(recording_root=str(tmp_path))
    captured_content = {}

    async def fake_exec(*args, **kwargs):
        # args 形如 (ffmpeg, -hide_banner, ..., -i, <concat_list>, ..., <output>)
        i_idx = args.index("-i")
        concat_path = Path(args[i_idx + 1])
        captured_content["text"] = concat_path.read_text(encoding="utf-8")
        out = Path(args[-1])
        out.write_bytes(b"x" * 100)
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))
        return proc

    with patch(
        "services.clip_service.asyncio.create_subprocess_exec",
        new=fake_exec,
    ), patch(
        "services.clip_service.storage_service.upload_alert_clip",
        new=AsyncMock(return_value="ok"),
    ):
        await svc.create_alert_clip(
            alert_id="alert-5",
            stream_id="cam01",
            trigger_ts=ts.replace(second=5),
        )

    text = captured_content["text"]
    lines = [l for l in text.splitlines() if l.strip()]
    assert len(lines) == 2
    assert lines[0].startswith("file '") and lines[0].endswith("'")
    # 升序：seg0 的路径应在 seg1 之前
    assert seg0.as_posix() in lines[0]
    assert seg1.as_posix() in lines[1]


@pytest.mark.asyncio
async def test_create_clip_handles_tz_aware_trigger(tmp_path: Path):
    """传入 tz-aware 的 trigger_ts 不崩溃（按 naive 本地时间处理）。"""
    ts_aware = datetime(2026, 4, 19, 10, 30, 5, tzinfo=timezone.utc)
    _make_segment(tmp_path, "cam01", datetime(2026, 4, 19, 10, 30, 0))

    svc = ClipService(recording_root=str(tmp_path))

    async def fake_exec(*args, **kwargs):
        out = Path(args[-1])
        out.write_bytes(b"x" * 100)
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate = AsyncMock(return_value=(b"", b""))
        return proc

    with patch(
        "services.clip_service.asyncio.create_subprocess_exec",
        new=fake_exec,
    ), patch(
        "services.clip_service.storage_service.upload_alert_clip",
        new=AsyncMock(return_value="ok"),
    ):
        result = await svc.create_alert_clip(
            alert_id="alert-tz",
            stream_id="cam01",
            trigger_ts=ts_aware,
        )
    assert result == "ok"
