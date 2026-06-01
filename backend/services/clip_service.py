"""告警视频片段生成服务

根据告警时间戳，从 mediamtx 滚动录制目录中裁剪出"前 N 秒 + 后 M 秒"的 MP4 片段，
通过 ffmpeg concat copy remux（不转码，零损耗），上传到 MinIO alert-clips 桶。

调用方（Week 3B 的 AlertService scheduler）需要保证：
    - trigger_ts 与 mediamtx segment 文件名的时区一致（默认容器时区，通常 UTC）
    - post_seconds 后等待至少 post_seconds + 2~3s 再调用，确保相关 segment 已落盘

本服务对外暴露 create_alert_clip 一个方法，**任何失败都返回 None，不抛异常**，
让 scheduler 可以安全重试或跳过该告警。
"""

import asyncio
import logging
import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from config.settings import MediaMTXConfig
from services.mediamtx_client import (
    DEFAULT_SEGMENT_DURATION_SECONDS,
    MediaMTXClient,
    RecordingSegment,
)
from services.storage import storage_service
from utils.async_helpers import run_blocking

logger = logging.getLogger(__name__)

# UUID 格式正则（用于 stream_id 判定）
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class ClipService:
    """告警视频片段生成服务。"""

    # 容器内 mediamtx 录制根目录（从 MediaMTXConfig 读取）
    RECORDING_ROOT = MediaMTXConfig.RECORDING_ROOT
    # MinIO 目标桶
    BUCKET = "alert-clips"
    # ffmpeg 二进制，容器内应在 PATH 中
    FFMPEG_BIN = os.getenv("FFMPEG_BIN", "ffmpeg")

    def __init__(
        self,
        recording_root: Optional[str] = None,
        segment_duration_seconds: Optional[int] = None,
    ) -> None:
        self.recording_root = recording_root or MediaMTXConfig.RECORDING_ROOT
        self.segment_duration_seconds = (
            segment_duration_seconds or MediaMTXConfig.RECORD_SEGMENT_DURATION
        )

    @staticmethod
    def _resolve_mediamtx_path(stream_id_or_path: str) -> Optional[str]:
        """将 stream_id（UUID 字符串）映射到 mediamtx path 名。

        与 StreamService._to_path_name 保持一致的规则：UUID 去掉连字符即 path。
        如果传入的不是 UUID，则视为已是 path 名直接返回（幂等）。
        完全解析失败返回 None，调用方自行决定跳过或兜底。
        """
        if not stream_id_or_path:
            return None
        if _UUID_RE.match(stream_id_or_path):
            return stream_id_or_path.replace("-", "")
        # 非 UUID：可能已经是 path 名（测试/兼容场景）
        return stream_id_or_path

    async def create_alert_clip(
        self,
        alert_id: str,
        stream_id: str,
        trigger_ts: datetime,
        pre_seconds: int = 5,
        post_seconds: int = 10,
    ) -> Optional[str]:
        """生成告警片段并上传 MinIO。

        Args:
            alert_id: 告警 ID，用作 MinIO key 和临时文件名
            stream_id: 对应 mediamtx path 名（录制子目录）
            trigger_ts: 告警触发时间戳（naive datetime，需与 segment 文件名时区一致）
            pre_seconds: 向前扩展秒数，默认 5
            post_seconds: 向后扩展秒数，默认 10

        Returns:
            成功返回可访问 URL；任何失败返回 None（不抛异常）。
        """
        try:
            # stream_id 入参语义：AlertDB.stream_id 是 UUID，而 mediamtx 录制目录按 path 名组织
            # 这里统一转成 path 名（去连字符），避免 list_recording_segments 扫到不存在的目录
            mediamtx_path = self._resolve_mediamtx_path(stream_id)
            if not mediamtx_path:
                logger.warning(
                    f"[ClipService] 无法解析 mediamtx path，跳过 alert_id={alert_id} "
                    f"stream_id={stream_id}"
                )
                return None
            if mediamtx_path != stream_id:
                logger.debug(
                    f"[ClipService] stream_id={stream_id} -> mediamtx_path={mediamtx_path}"
                )

            # 若传入 timezone-aware，去除 tz 保持 naive（mediamtx segment 文件名无时区信息）
            if trigger_ts.tzinfo is not None:
                logger.info(
                    f"[ClipService] 收到 tz-aware trigger_ts={trigger_ts.isoformat()}, "
                    f"将按容器本地时间解读（mediamtx 默认 UTC）"
                )
                trigger_ts = trigger_ts.replace(tzinfo=None)

            window_start = trigger_ts - timedelta(seconds=pre_seconds)
            window_end = trigger_ts + timedelta(seconds=post_seconds)

            logger.info(
                f"[ClipService] alert_id={alert_id} stream_id={stream_id} "
                f"trigger={trigger_ts.isoformat()} "
                f"window=[{window_start.isoformat()}, {window_end.isoformat()}]"
            )

            # 1. 扫描 segments（同步 glob，run_in_thread 避免阻塞事件循环）
            segments: List[RecordingSegment] = await run_blocking(
                MediaMTXClient.list_recording_segments,
                stream_id=mediamtx_path,
                window_start=window_start,
                window_end=window_end,
                recording_root=self.recording_root,
                segment_duration_seconds=self.segment_duration_seconds,
            )

            if not segments:
                logger.warning(
                    f"[ClipService] 未找到匹配 segment，跳过 alert_id={alert_id}"
                )
                return None

            # 2. 生成 ffmpeg concat list + 目标 mp4 到临时目录
            with tempfile.TemporaryDirectory(prefix="clip_") as tmpdir:
                tmp_path = Path(tmpdir)
                concat_list_path = tmp_path / "concat.txt"
                output_mp4_path = tmp_path / f"{alert_id}.mp4"

                # concat demuxer 要求每行 `file '<absolute path>'`
                concat_lines = [f"file '{seg.path.as_posix()}'" for seg in segments]
                concat_list_path.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

                logger.debug(
                    f"[ClipService] alert_id={alert_id} segments={len(segments)} "
                    f"concat_list={concat_list_path}"
                )

                # 3. 异步调用 ffmpeg concat + copy remux
                ok = await self._run_ffmpeg_concat(
                    concat_list_path=concat_list_path,
                    output_path=output_mp4_path,
                )
                if not ok:
                    logger.error(f"[ClipService] ffmpeg 合成失败 alert_id={alert_id}")
                    return None

                if not output_mp4_path.exists() or output_mp4_path.stat().st_size == 0:
                    logger.error(
                        f"[ClipService] ffmpeg 产物为空 alert_id={alert_id} "
                        f"path={output_mp4_path}"
                    )
                    return None

                # 4. 上传 MinIO
                try:
                    clip_url = await storage_service.upload_alert_clip(
                        alert_id=alert_id,
                        local_mp4_path=str(output_mp4_path),
                    )
                except Exception as upload_err:
                    logger.error(
                        f"[ClipService] MinIO 上传失败 alert_id={alert_id}: {upload_err}"
                    )
                    return None

                logger.info(
                    f"[ClipService] 片段生成完成 alert_id={alert_id} url={clip_url}"
                )
                return clip_url
                # with 块退出自动清理 tmpdir（concat.txt + mp4）

        except Exception as e:
            # 顶层兜底：永不抛异常给调用方
            logger.exception(
                f"[ClipService] 意外失败 alert_id={alert_id} stream_id={stream_id}: {e}"
            )
            return None

    async def _run_ffmpeg_concat(
        self,
        concat_list_path: Path,
        output_path: Path,
    ) -> bool:
        """使用 ffmpeg concat demuxer + copy remux 合并 segment。

        - `-f concat -safe 0`：允许绝对路径
        - `-c copy`：零转码，直接拷贝码流
        - `-movflags +faststart`：moov 前置，便于浏览器流式播放
        - `-y`：覆盖已存在输出

        成功返回 True；非零退出码或子进程启动失败返回 False。
        """
        args = [
            self.FFMPEG_BIN,
            "-hide_banner",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_path),
            "-c", "copy",
            "-movflags", "+faststart",
            "-y",
            str(output_path),
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode != 0:
                logger.error(
                    f"[ClipService] ffmpeg 非零退出 code={proc.returncode} "
                    f"stderr={stderr.decode('utf-8', errors='replace').strip()}"
                )
                return False
            return True
        except FileNotFoundError:
            logger.error(f"[ClipService] ffmpeg 二进制未找到: {self.FFMPEG_BIN}")
            return False
        except Exception as e:
            logger.error(f"[ClipService] ffmpeg 调用异常: {e}")
            return False


# 全局单例（与 storage_service 一致的习惯）
clip_service = ClipService()
