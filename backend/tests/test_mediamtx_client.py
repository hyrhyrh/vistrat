"""MediaMTXClient.list_recording_segments 单元测试"""

from datetime import datetime
from pathlib import Path

from services.mediamtx_client import MediaMTXClient, RecordingSegment


def _touch_segment(base_dir: Path, stream_id: str, ts: datetime) -> Path:
    d = base_dir / stream_id
    d.mkdir(parents=True, exist_ok=True)
    name = ts.strftime("%Y-%m-%d_%H-%M-%S-") + f"{ts.microsecond:06d}.mp4"
    p = d / name
    p.write_bytes(b"x")
    return p


def test_list_segments_sorted_ascending(tmp_path: Path):
    base = datetime(2026, 4, 19, 10, 0, 0)
    # 故意乱序创建
    _touch_segment(tmp_path, "cam", base.replace(second=20))
    _touch_segment(tmp_path, "cam", base)
    _touch_segment(tmp_path, "cam", base.replace(second=10))

    segs = MediaMTXClient.list_recording_segments(
        stream_id="cam",
        window_start=base,
        window_end=base.replace(second=30),
        recording_root=str(tmp_path),
    )
    assert [s.start_ts.second for s in segs] == [0, 10, 20]


def test_list_segments_end_boundary_included(tmp_path: Path):
    """窗口终点落在某 segment 中间 → 该 segment 应包含。"""
    base = datetime(2026, 4, 19, 10, 0, 0)
    _touch_segment(tmp_path, "cam", base)
    _touch_segment(tmp_path, "cam", base.replace(second=10))  # 覆盖 [10, 20)
    _touch_segment(tmp_path, "cam", base.replace(second=20))  # 不应包含

    segs = MediaMTXClient.list_recording_segments(
        stream_id="cam",
        window_start=base.replace(second=5),
        window_end=base.replace(second=15),
        recording_root=str(tmp_path),
        segment_duration_seconds=10,
    )
    starts = [s.start_ts.second for s in segs]
    assert 0 in starts and 10 in starts
    assert 20 not in starts


def test_list_segments_invalid_window(tmp_path: Path):
    """window_end < window_start 直接返回空。"""
    _touch_segment(tmp_path, "cam", datetime(2026, 4, 19, 10, 0, 0))
    segs = MediaMTXClient.list_recording_segments(
        stream_id="cam",
        window_start=datetime(2026, 4, 19, 10, 0, 10),
        window_end=datetime(2026, 4, 19, 10, 0, 0),
        recording_root=str(tmp_path),
    )
    assert segs == []


def test_list_segments_est_end_ts_correct(tmp_path: Path):
    base = datetime(2026, 4, 19, 10, 0, 0)
    _touch_segment(tmp_path, "cam", base)
    segs = MediaMTXClient.list_recording_segments(
        stream_id="cam",
        window_start=base,
        window_end=base.replace(second=30),
        recording_root=str(tmp_path),
        segment_duration_seconds=10,
    )
    assert len(segs) == 1
    assert segs[0].est_end_ts == base.replace(second=10)
    assert isinstance(segs[0], RecordingSegment)
