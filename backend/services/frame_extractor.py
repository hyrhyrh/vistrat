"""智能三级抽帧服务"""

import asyncio
import logging
import random
import time
from dataclasses import dataclass

import cv2
import numpy as np

from config.settings import FrameConfig
from utils.ffmpeg_decoder import FFmpegDecoder

logger = logging.getLogger(__name__)


@dataclass
class FrameData:
    """抽帧结果数据"""
    frame: np.ndarray
    timestamp: float
    reason: str  # "motion" | "scene_change" | "fallback_timer"
    task_id: str


class MotionDetector:
    """运动检测 — 帧差法"""

    def __init__(
        self,
        threshold: float = FrameConfig.MOTION_THRESHOLD,
        min_area_ratio: float = FrameConfig.MOTION_MIN_AREA_RATIO,
        reference_weight: float = FrameConfig.REFERENCE_FRAME_WEIGHT,
    ):
        self.threshold = threshold
        self.min_area_ratio = min_area_ratio
        self.reference_weight = reference_weight
        self.reference_frame: np.ndarray | None = None

    def detect(self, frame: np.ndarray) -> bool:
        """检测帧中是否存在运动"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.reference_frame is None:
            self.reference_frame = gray
            return True

        diff = cv2.absdiff(self.reference_frame, gray)
        _, thresh = cv2.threshold(diff, int(self.threshold), 255, cv2.THRESH_BINARY)
        thresh = cv2.dilate(thresh, None, iterations=2)

        motion_ratio = cv2.countNonZero(thresh) / thresh.size

        # 渐进式更新参考帧，避免光照漂移
        self.reference_frame = cv2.addWeighted(
            self.reference_frame, self.reference_weight,
            gray, 1 - self.reference_weight, 0,
        ).astype(np.uint8)

        return motion_ratio > self.min_area_ratio


class SceneChangeDetector:
    """场景变化检测 — 直方图相关性"""

    def __init__(self, change_threshold: float = FrameConfig.SCENE_CHANGE_THRESHOLD):
        self.change_threshold = change_threshold
        self.prev_hist: np.ndarray | None = None

    def detect(self, frame: np.ndarray) -> bool:
        """检测是否发生场景切换"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        cv2.normalize(hist, hist)

        if self.prev_hist is None:
            self.prev_hist = hist
            return False

        correlation = cv2.compareHist(self.prev_hist, hist, cv2.HISTCMP_CORREL)
        self.prev_hist = hist

        return correlation < self.change_threshold


class FrameExtractor:
    """三级智能抽帧器

    策略优先级: 运动检测 → 场景变化 → 保底定时
    通过 asyncio.Queue 与下游分析服务解耦。
    """

    def __init__(self, stream_url: str, output_queue: asyncio.Queue, task_id: str):
        self.stream_url = stream_url
        self.output_queue = output_queue
        self.task_id = task_id
        self.running = False

        self.decoder = FFmpegDecoder(rtsp_url=stream_url)
        self.motion_detector = MotionDetector()
        self.scene_detector = SceneChangeDetector()

        # 统计
        self.frames_extracted = 0
        self.frames_checked = 0

    async def run(self) -> None:
        """主抽帧循环"""
        if not self.decoder.start():
            logger.error(f"[{self.task_id}] FFmpegDecoder 启动失败: {self.stream_url}")
            return

        self.running = True
        last_extract_time = 0.0
        last_sample_time = 0.0
        loop = asyncio.get_event_loop()

        # 启动 watchdog 协程
        watchdog_task = asyncio.create_task(self._watchdog())

        try:
            while self.running:
                now = time.time()

                # 采样控制：按 MOTION_SAMPLE_INTERVAL 间隔读帧
                elapsed_since_sample = now - last_sample_time
                if elapsed_since_sample < FrameConfig.MOTION_SAMPLE_INTERVAL:
                    await asyncio.sleep(
                        FrameConfig.MOTION_SAMPLE_INTERVAL - elapsed_since_sample
                    )
                    now = time.time()

                last_sample_time = now

                # 在线程池中读帧，避免阻塞事件循环
                ok, frame = await loop.run_in_executor(None, self.decoder.read, 2.0)
                if not ok or frame is None:
                    continue

                self.frames_checked += 1
                reason: str | None = None

                # 三级策略判断
                if self.motion_detector.detect(frame):
                    reason = "motion"
                elif self.scene_detector.detect(frame):
                    reason = "scene_change"
                elif (now - last_extract_time) >= FrameConfig.FALLBACK_INTERVAL:
                    reason = "fallback_timer"

                if reason is None:
                    # 即使不抽帧也要检测场景变化以更新内部状态
                    if reason != "scene_change":
                        self.scene_detector.detect(frame)
                    continue

                # 输出帧到队列
                frame_data = FrameData(
                    frame=frame, timestamp=now, reason=reason, task_id=self.task_id
                )
                try:
                    self.output_queue.put_nowait(frame_data)
                    self.frames_extracted += 1
                    last_extract_time = now
                except asyncio.QueueFull:
                    logger.warning(
                        f"[{self.task_id}] 帧队列已满，丢弃当前帧 (reason={reason})"
                    )

        except asyncio.CancelledError:
            logger.info(f"[{self.task_id}] 抽帧循环被取消")
        except Exception as e:
            logger.error(f"[{self.task_id}] 抽帧循环异常: {e}")
        finally:
            watchdog_task.cancel()
            try:
                await watchdog_task
            except asyncio.CancelledError:
                pass
            self.decoder.stop()
            self.running = False
            logger.info(
                f"[{self.task_id}] 抽帧结束: 检查 {self.frames_checked} 帧, "
                f"提取 {self.frames_extracted} 帧"
            )

    async def stop(self) -> None:
        """停止抽帧"""
        self.running = False
        self.decoder.stop()

    async def _watchdog(self) -> None:
        """Watchdog 协程 — 监控 ffmpeg 进程健康，自动重启"""
        attempt = 0

        while self.running:
            await asyncio.sleep(FrameConfig.WATCHDOG_CHECK_INTERVAL)

            if not self.running:
                break

            if self.decoder.is_alive():
                attempt = 0
                continue

            attempt += 1
            logger.warning(
                f"[{self.task_id}] ffmpeg 进程异常，尝试重启 ({attempt}/{FrameConfig.WATCHDOG_MAX_RETRIES})"
            )

            if attempt > FrameConfig.WATCHDOG_MAX_RETRIES:
                logger.error(
                    f"[{self.task_id}] ffmpeg 重启次数超过上限 "
                    f"({FrameConfig.WATCHDOG_MAX_RETRIES})，停止抽帧"
                )
                self.running = False
                break

            if self.decoder.restart():
                logger.info(f"[{self.task_id}] ffmpeg 重启成功")
                attempt = 0
            else:
                delay = min(
                    FrameConfig.WATCHDOG_BASE_DELAY * (2 ** attempt),
                    FrameConfig.WATCHDOG_MAX_DELAY,
                )
                jitter = random.uniform(0, delay * 0.1)
                total_delay = delay + jitter
                logger.warning(
                    f"[{self.task_id}] ffmpeg 重启失败，{total_delay:.1f}s 后重试"
                )
                await asyncio.sleep(total_delay)
