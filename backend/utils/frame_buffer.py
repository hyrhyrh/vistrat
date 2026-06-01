"""
视频帧缓冲和质量选择器
缓冲多个帧，选择质量最好的帧进行处理
避免处理模糊的P帧/B帧
"""

import numpy as np
import logging
from collections import deque
from typing import Optional, Tuple, Deque
from dataclasses import dataclass

from utils.frame_quality_checker import frame_quality_checker, FrameQualityMetrics

logger = logging.getLogger(__name__)


@dataclass
class BufferedFrame:
    """缓冲帧数据"""
    frame: np.ndarray
    frame_index: int
    timestamp: float
    quality_metrics: FrameQualityMetrics


class FrameQualityBuffer:
    """
    帧质量缓冲器
    缓冲多个帧，选择质量最好的帧
    """

    def __init__(
        self,
        buffer_size: int = 10,  # 缓冲区大小
        min_quality_score: float = 60.0,  # 最低质量分数
        enable_quality_filter: bool = True,  # 是否启用质量过滤
    ):
        """
        初始化帧缓冲器

        Args:
            buffer_size: 缓冲区大小，建议5-15帧
            min_quality_score: 最低质量分数(0-100)，低于此分数的帧会被过滤
            enable_quality_filter: 是否启用质量过滤
        """
        self.buffer_size = buffer_size
        self.min_quality_score = min_quality_score
        self.enable_quality_filter = enable_quality_filter
        self.buffer: Deque[BufferedFrame] = deque(maxlen=buffer_size)

        # 统计信息
        self.total_frames_received = 0
        self.total_frames_filtered = 0
        self.total_frames_selected = 0

    def add_frame(
        self, frame: np.ndarray, frame_index: int, timestamp: float
    ) -> None:
        """
        添加帧到缓冲区

        Args:
            frame: 视频帧
            frame_index: 帧索引
            timestamp: 时间戳
        """
        try:
            self.total_frames_received += 1

            # 评估帧质量
            quality_metrics = frame_quality_checker.check_frame_quality(
                frame, verbose=False
            )

            # 如果启用质量过滤且质量太低，直接丢弃
            if self.enable_quality_filter and quality_metrics.quality_score < self.min_quality_score:
                self.total_frames_filtered += 1
                logger.debug(
                    f"⚠️ 帧{frame_index}质量过低({quality_metrics.quality_score:.2f}), "
                    f"清晰度={quality_metrics.sharpness:.2f}, 已过滤"
                )
                return

            # 添加到缓冲区
            buffered_frame = BufferedFrame(
                frame=frame.copy(),  # 深拷贝避免引用问题
                frame_index=frame_index,
                timestamp=timestamp,
                quality_metrics=quality_metrics,
            )

            self.buffer.append(buffered_frame)

            logger.debug(
                f"✅ 帧{frame_index}已加入缓冲区, "
                f"质量分数={quality_metrics.quality_score:.2f}, "
                f"缓冲区大小={len(self.buffer)}/{self.buffer_size}"
            )

        except Exception as e:
            logger.error(f"添加帧到缓冲区失败: {e}")

    def get_best_frame(self) -> Optional[BufferedFrame]:
        """
        从缓冲区获取质量最好的帧

        Returns:
            质量最好的帧，如果缓冲区为空或没有合格帧则返回None
        """
        try:
            if not self.buffer:
                logger.debug("缓冲区为空，无法获取最佳帧")
                return None

            # 按质量分数排序，选择最高分的帧
            best_frame = max(self.buffer, key=lambda bf: bf.quality_metrics.quality_score)

            # 再次检查质量是否达标
            if best_frame.quality_metrics.quality_score < self.min_quality_score:
                logger.warning(
                    f"⚠️ 缓冲区最佳帧质量仍不达标: "
                    f"分数={best_frame.quality_metrics.quality_score:.2f}, "
                    f"阈值={self.min_quality_score}"
                )
                return None

            self.total_frames_selected += 1

            logger.debug(
                f"🎯 选中最佳帧: 帧{best_frame.frame_index}, "
                f"质量分数={best_frame.quality_metrics.quality_score:.2f}, "
                f"清晰度={best_frame.quality_metrics.sharpness:.2f}, "
                f"亮度={best_frame.quality_metrics.brightness:.2f}, "
                f"对比度={best_frame.quality_metrics.contrast:.2f}"
            )

            return best_frame

        except Exception as e:
            logger.error(f"获取最佳帧失败: {e}")
            return None

    def get_best_frame_and_clear(self) -> Optional[BufferedFrame]:
        """
        获取最佳帧并清空缓冲区

        常用于周期性处理场景

        Returns:
            质量最好的帧
        """
        best_frame = self.get_best_frame()
        self.clear()
        return best_frame

    def clear(self) -> None:
        """清空缓冲区"""
        self.buffer.clear()
        logger.debug("🧹 缓冲区已清空")

    def is_full(self) -> bool:
        """检查缓冲区是否已满"""
        return len(self.buffer) >= self.buffer_size

    def get_statistics(self) -> dict:
        """
        获取统计信息

        Returns:
            统计数据字典
        """
        filter_rate = (
            (self.total_frames_filtered / self.total_frames_received * 100)
            if self.total_frames_received > 0
            else 0
        )
        select_rate = (
            (self.total_frames_selected / self.total_frames_received * 100)
            if self.total_frames_received > 0
            else 0
        )

        return {
            "total_received": self.total_frames_received,
            "total_filtered": self.total_frames_filtered,
            "total_selected": self.total_frames_selected,
            "filter_rate": f"{filter_rate:.2f}%",
            "select_rate": f"{select_rate:.2f}%",
            "buffer_size": len(self.buffer),
            "buffer_capacity": self.buffer_size,
        }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.total_frames_received = 0
        self.total_frames_filtered = 0
        self.total_frames_selected = 0
        logger.info("📊 帧缓冲统计信息已重置")


class StreamFrameSelector:
    """
    流式帧选择器（企业级质量保证）

    在实时流中周期性选择最佳帧
    避免缓冲区无限增长
    ✨ 极严格质量标准，确保100%清晰图片
    """

    def __init__(
        self,
        selection_interval: int = 10,  # 每N帧选择一次最佳帧
        buffer_size: int = 10,
        min_quality_score: float = 80.0,  # ✨ 提升：60 → 80（极严格）
    ):
        """
        初始化流式帧选择器

        Args:
            selection_interval: 选择间隔(帧数)
            buffer_size: 缓冲区大小
            min_quality_score: 最低质量分数
        """
        self.selection_interval = selection_interval
        self.buffer = FrameQualityBuffer(
            buffer_size=buffer_size, min_quality_score=min_quality_score
        )
        self.frame_count = 0

    def process_frame(
        self, frame: np.ndarray, frame_index: int, timestamp: float
    ) -> Optional[BufferedFrame]:
        """
        处理新帧

        Args:
            frame: 视频帧
            frame_index: 帧索引
            timestamp: 时间戳

        Returns:
            如果到达选择间隔，返回最佳帧；否则返回None
        """
        self.frame_count += 1

        # 添加到缓冲区
        self.buffer.add_frame(frame, frame_index, timestamp)

        # 检查是否到达选择间隔
        if self.frame_count >= self.selection_interval:
            best_frame = self.buffer.get_best_frame_and_clear()
            self.frame_count = 0  # 重置计数

            if best_frame:
                logger.info(
                    f"🎯 周期选择: 在{self.selection_interval}帧中选出最佳帧{best_frame.frame_index}, "
                    f"质量分数={best_frame.quality_metrics.quality_score:.2f}"
                )
            else:
                logger.warning(f"⚠️ 最近{self.selection_interval}帧中没有合格的清晰帧")

            return best_frame

        return None

    def get_statistics(self) -> dict:
        """获取统计信息"""
        stats = self.buffer.get_statistics()
        stats["selection_interval"] = self.selection_interval
        stats["current_frame_count"] = self.frame_count
        return stats
