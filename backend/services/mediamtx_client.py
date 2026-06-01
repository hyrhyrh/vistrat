"""mediamtx REST API client -- manages RTSP stream paths + 录制 segment 扫描"""
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import httpx
from config.settings import MediaMTXConfig

logger = logging.getLogger(__name__)


# mediamtx recordPath 格式: /recordings/{path}/%Y-%m-%d_%H-%M-%S-%f.mp4
# 例如: /recordings/cam01/2026-04-19_10-30-00-123456.mp4
_SEGMENT_NAME_RE = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{6})$"
)
_SEGMENT_TS_FORMAT = "%Y-%m-%d_%H-%M-%S-%f"

# 默认 segment 时长（秒），与 mediamtx.yml 中 recordSegmentDuration 对齐
# 从 MediaMTXConfig 读取，留做向后兼容的模块级常量
DEFAULT_SEGMENT_DURATION_SECONDS = MediaMTXConfig.RECORD_SEGMENT_DURATION


@dataclass
class RecordingSegment:
    """录制分段文件的元数据。

    - path: segment 文件绝对路径（容器内）
    - start_ts: 文件名解析得到的起始时间戳（naive datetime，容器时区）
    - est_end_ts: start_ts + segment_duration，近似结束时间（不读取文件真实时长）
    """

    path: Path
    start_ts: datetime
    est_end_ts: datetime


def _parse_segment_timestamp(filename_stem: str) -> Optional[datetime]:
    """从 segment 文件名 stem 解析时间戳。失败返回 None。"""
    m = _SEGMENT_NAME_RE.match(filename_stem)
    if not m:
        return None
    try:
        return datetime.strptime(m.group("ts"), _SEGMENT_TS_FORMAT)
    except ValueError:
        return None


class MediaMTXClient:
    """mediamtx /v3/ Control API async client"""

    def __init__(self):
        self.base_url = MediaMTXConfig.get_api_url()

    async def add_path(self, name: str, source_url: str) -> bool:
        """Register an RTSP source. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/v3/config/paths/add/{name}",
                    json={"source": source_url, "sourceOnDemand": True},
                )
                success = resp.status_code in (200, 201)
                if success:
                    logger.info(f"mediamtx: registered path '{name}' -> {source_url}")
                else:
                    logger.warning(
                        f"mediamtx: failed to register '{name}', "
                        f"status={resp.status_code}, body={resp.text}"
                    )
                return success
        except httpx.RequestError as e:
            logger.error(f"mediamtx: connection error adding path '{name}': {e}")
            return False

    async def remove_path(self, name: str) -> bool:
        """Remove a mediamtx path. Returns True on success."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    f"{self.base_url}/v3/config/paths/delete/{name}"
                )
                success = resp.status_code in (200, 204)
                if success:
                    logger.info(f"mediamtx: removed path '{name}'")
                else:
                    logger.warning(
                        f"mediamtx: failed to remove '{name}', status={resp.status_code}"
                    )
                return success
        except httpx.RequestError as e:
            logger.error(f"mediamtx: connection error removing path '{name}': {e}")
            return False

    async def list_paths(self) -> dict:
        """List all active mediamtx paths."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.base_url}/v3/paths/list")
            resp.raise_for_status()
            return resp.json()

    async def health_check(self) -> bool:
        """Check if mediamtx API is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/v3/paths/list")
                return resp.status_code == 200
        except httpx.RequestError:
            return False

    async def sync_all_paths(self, streams: list[dict]) -> int:
        """Re-register all active streams. Returns count of successful registrations.
        Called on backend startup to handle mediamtx restart (dynamic paths don't persist).
        Each dict must have 'name' (path name) and 'source_url' (RTSP URL)."""
        registered = 0
        for stream in streams:
            if await self.add_path(stream["name"], stream["source_url"]):
                registered += 1
        logger.info(f"mediamtx: sync complete, {registered}/{len(streams)} paths registered")
        return registered

    @staticmethod
    def list_recording_segments(
        stream_id: str,
        window_start: datetime,
        window_end: datetime,
        recording_root: str = "/recordings",
        segment_duration_seconds: int = DEFAULT_SEGMENT_DURATION_SECONDS,
    ) -> List[RecordingSegment]:
        """扫描 mediamtx 录制目录，返回落在 [window_start, window_end] 窗口内的 segment。

        窗口匹配规则（包含跨边界的 segment）：
            保留 segment 的条件为 `start_ts <= window_end AND est_end_ts >= window_start`，
            因此窗口起点落在 segment 中间、窗口终点落在另一 segment 中间的情况都能覆盖到。

        纯同步 + pathlib glob；不打开 mp4 读真实时长，end 以 segment_duration_seconds 估算。

        Args:
            stream_id: 对应 mediamtx path 名，作为录制目录的子目录
            window_start: 窗口起点（naive datetime，需与 segment 文件名时区一致）
            window_end: 窗口终点
            recording_root: 容器内录制根路径
            segment_duration_seconds: 单 segment 预估时长，默认 10s

        Returns:
            按 start_ts 升序排列的 segment 列表；目录不存在或无匹配时返回空列表。
        """
        root = Path(recording_root) / stream_id
        if not root.exists() or not root.is_dir():
            logger.warning(
                f"list_recording_segments: 目录不存在 stream_id={stream_id} path={root}"
            )
            return []

        if window_end < window_start:
            logger.warning(
                f"list_recording_segments: 无效窗口 start={window_start} end={window_end}"
            )
            return []

        seg_delta = timedelta(seconds=segment_duration_seconds)
        results: List[RecordingSegment] = []

        # 录制格式为 fmp4，文件后缀 .mp4；兼容 .ts 保底（MediaMTX 某些旧版本）
        for p in list(root.glob("*.mp4")) + list(root.glob("*.ts")):
            if not p.is_file():
                continue
            ts = _parse_segment_timestamp(p.stem)
            if ts is None:
                continue
            est_end = ts + seg_delta
            # 跨边界判断：segment 与窗口有任何重叠即纳入
            if ts <= window_end and est_end >= window_start:
                results.append(
                    RecordingSegment(path=p, start_ts=ts, est_end_ts=est_end)
                )

        results.sort(key=lambda s: s.start_ts)
        logger.info(
            f"list_recording_segments: stream_id={stream_id} "
            f"window=[{window_start}, {window_end}] matched={len(results)}"
        )
        return results
