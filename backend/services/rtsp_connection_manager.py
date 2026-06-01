"""
RTSP连接管理器
提供智能重连、指数退避和连接健康度监控功能
优化方案1: 智能重连机制
"""

import asyncio
import time
import logging
from typing import Optional, Dict, Any, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RTSPConnectionManager:
    """RTSP连接管理器 - 提供智能重连和健康度监控"""

    def __init__(self, max_retries=10, initial_delay=1, max_delay=60):
        """
        初始化RTSP连接管理器

        Args:
            max_retries: 最大重试次数
            initial_delay: 初始延迟时间(秒)
            max_delay: 最大延迟时间(秒)
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.retry_count = 0
        self.last_success_time = None
        self.total_reconnects = 0  # 总重连次数
        self.connection_failures = 0  # 连续失败次数

    async def connect_with_retry(self, rtsp_url: str) -> Optional[cv2.VideoCapture]:
        """
        带重试的RTSP连接

        Args:
            rtsp_url: RTSP流地址

        Returns:
            VideoCapture对象,失败返回None
        """
        self.retry_count = 0

        while self.retry_count < self.max_retries:
            try:
                logger.debug(f"尝试连接RTSP流: {rtsp_url} (第{self.retry_count + 1}次)")

                # 创建VideoCapture对象
                cap = cv2.VideoCapture(rtsp_url)

                if cap.isOpened():
                    # 连接成功
                    self.last_success_time = time.time()
                    self.retry_count = 0  # 重置重试计数
                    self.connection_failures = 0  # 重置连续失败计数

                    if self.total_reconnects > 0:
                        logger.info(
                            f"✓ RTSP重连成功: {rtsp_url} "
                            f"(历史重连次数: {self.total_reconnects})"
                        )
                    else:
                        logger.info(f"✓ RTSP连接成功: {rtsp_url}")

                    return cap

                # 连接失败,计算退避时间
                delay = min(
                    self.initial_delay * (2 ** self.retry_count),
                    self.max_delay
                )
                self.retry_count += 1
                self.connection_failures += 1

                logger.warning(
                    f"✗ RTSP连接失败,{delay}秒后重试 "
                    f"(第{self.retry_count}/{self.max_retries}次) "
                    f"- {rtsp_url}"
                )

                # 指数退避等待
                await asyncio.sleep(delay)

            except Exception as e:
                logger.error(f"✗ RTSP连接异常: {e}")
                self.retry_count += 1
                self.connection_failures += 1

                # 异常时使用初始延迟
                await asyncio.sleep(self.initial_delay)

        # 超过最大重试次数
        logger.error(
            f"✗ RTSP连接失败,已达最大重试次数 ({self.max_retries}) "
            f"- {rtsp_url}"
        )
        return None

    async def read_frame_with_retry(
        self,
        cap: cv2.VideoCapture,
        rtsp_url: str
    ) -> Tuple[bool, Optional[np.ndarray], Optional[cv2.VideoCapture]]:
        """
        带重试的帧读取（线程池执行避免阻塞事件循环）

        Args:
            cap: 当前VideoCapture对象
            rtsp_url: RTSP流地址

        Returns:
            (成功标志, 帧数据, 新的VideoCapture对象)
            如果返回新的VideoCapture对象,调用方应该使用新对象替换旧对象
        """
        # NOTE(async): OpenCV VideoCapture.read() 是阻塞调用，必须在线程池中运行
        # 避免在 Windows/Linux 事件循环中阻塞主线程（解决 RTSP 流卡死问题）
        loop = asyncio.get_running_loop()
        ret, frame = await loop.run_in_executor(None, cap.read)

        if not ret:
            # 读取失败,尝试重新连接
            logger.warning(f"⚠ 帧读取失败,尝试重新连接RTSP流...")

            # 释放旧连接
            try:
                cap.release()
            except Exception as e:
                logger.warning(f"释放旧连接时出错: {e}")

            # 尝试重新连接
            self.total_reconnects += 1
            new_cap = await self.connect_with_retry(rtsp_url)

            if new_cap:
                # 重连成功,尝试读取一帧验证（同样放到线程池避免阻塞）
                ret, frame = await loop.run_in_executor(None, new_cap.read)
                if ret:
                    logger.info("✓ 重连后成功读取帧")
                    return ret, frame, new_cap
                else:
                    logger.warning("✗ 重连成功但无法读取帧")
                    return False, None, new_cap

            # 重连失败
            return False, None, None

        # 读取成功,重置重试计数
        if self.retry_count > 0:
            self.retry_count = 0

        return ret, frame, cap  # 返回原cap,无需替换

    def get_connection_health(self) -> Dict[str, Any]:
        """
        获取连接健康度

        Returns:
            包含健康状态的字典
        """
        if not self.last_success_time:
            return {
                'status': 'never_connected',
                'health_score': 0,
                'retry_count': self.retry_count,
                'connection_failures': self.connection_failures,
                'total_reconnects': self.total_reconnects,
                'uptime_seconds': 0
            }

        uptime = time.time() - self.last_success_time

        # 计算健康分数
        # 基础分数100,每次重试扣10分,最低0分
        health_score = max(0, min(100, 100 - self.retry_count * 10))

        # 根据连续失败次数调整健康分数
        if self.connection_failures > 5:
            health_score = max(0, health_score - 20)
        elif self.connection_failures > 3:
            health_score = max(0, health_score - 10)

        # 确定健康状态
        if health_score >= 80:
            status = 'healthy'
        elif health_score >= 50:
            status = 'degraded'
        else:
            status = 'unhealthy'

        return {
            'status': status,
            'health_score': health_score,
            'uptime_seconds': int(uptime),
            'retry_count': self.retry_count,
            'connection_failures': self.connection_failures,
            'total_reconnects': self.total_reconnects,
            'last_success_time': self.last_success_time
        }

    def reset_health_metrics(self):
        """重置健康指标(可用于手动恢复)"""
        self.retry_count = 0
        self.connection_failures = 0
        logger.info("✓ RTSP连接健康指标已重置")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取连接统计信息

        Returns:
            统计信息字典
        """
        health = self.get_connection_health()

        return {
            'health': health,
            'config': {
                'max_retries': self.max_retries,
                'initial_delay': self.initial_delay,
                'max_delay': self.max_delay
            },
            'metrics': {
                'total_reconnects': self.total_reconnects,
                'current_retry_count': self.retry_count,
                'connection_failures': self.connection_failures
            }
        }
