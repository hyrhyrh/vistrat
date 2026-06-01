"""
增强型自适应缓冲区管理器
根据系统负载和数据特征动态调整缓冲策略
优化方案2: 动态自适应缓冲
"""

import asyncio
import time
import logging
from typing import Dict, Any, Callable, Optional

logger = logging.getLogger(__name__)


class EnhancedAdaptiveBufferManager:
    """增强型自适应缓冲区管理器"""

    def __init__(self):
        self.buffers = {}
        self.metrics = {}  # 缓冲区指标
        self.flush_callback = None

        # 系统资源监控
        self.cpu_usage = 0.0
        self.memory_usage = 0.0
        self.active_streams = 0

        # 动态参数
        self.min_batch_size = 10
        self.max_batch_size = 200
        self.min_flush_interval = 10  # 秒
        self.max_flush_interval = 60  # 秒

        # 监控任务
        self._monitor_task = None
        self._running = False

    async def start(self):
        """启动缓冲区管理器"""
        if self._running:
            logger.warning("缓冲区管理器已在运行")
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_system_resources())
        logger.info("✅ 增强型自适应缓冲区管理器已启动")

    async def stop(self):
        """停止缓冲区管理器"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 增强型自适应缓冲区管理器已停止")

    async def _monitor_system_resources(self):
        """监控系统资源使用情况"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil未安装,无法监控系统资源,使用默认值")
            # 使用默认值
            self.cpu_usage = 0.5
            self.memory_usage = 0.5
            return

        while self._running:
            try:
                self.cpu_usage = psutil.cpu_percent(interval=1) / 100.0
                self.memory_usage = psutil.virtual_memory().percent / 100.0

                logger.debug(
                    f"系统资源: CPU={self.cpu_usage:.2%}, "
                    f"Memory={self.memory_usage:.2%}, "
                    f"Streams={self.active_streams}"
                )

            except Exception as e:
                logger.error(f"资源监控失败: {e}")

            await asyncio.sleep(5)

    def calculate_optimal_batch_size(self, buffer_key: str) -> int:
        """
        计算最优批量大小

        Args:
            buffer_key: 缓冲区键

        Returns:
            最优批量大小
        """
        # 基于系统负载的调整因子
        if self.cpu_usage > 0.8 or self.memory_usage > 0.8:
            load_factor = 0.5  # 高负载:小批量
        elif self.cpu_usage > 0.5 or self.memory_usage > 0.5:
            load_factor = 0.75  # 中负载:中批量
        else:
            load_factor = 1.0  # 低负载:大批量

        # 基于流数量的调整因子
        if self.active_streams > 10:
            stream_factor = 0.7
        elif self.active_streams > 5:
            stream_factor = 0.85
        else:
            stream_factor = 1.0

        # 基于缓冲区历史性能的调整
        metrics = self.metrics.get(buffer_key, {})
        avg_flush_time = metrics.get('avg_flush_time_ms', 100)

        if avg_flush_time > 1000:  # 刷新太慢
            time_factor = 0.8
        elif avg_flush_time > 500:
            time_factor = 0.9
        else:
            time_factor = 1.0

        # 综合计算
        base_size = (self.min_batch_size + self.max_batch_size) / 2
        optimal_size = int(base_size * load_factor * stream_factor * time_factor)

        return max(self.min_batch_size, min(optimal_size, self.max_batch_size))

    def calculate_optimal_flush_interval(self, buffer_key: str) -> float:
        """
        计算最优刷新间隔

        Args:
            buffer_key: 缓冲区键

        Returns:
            最优刷新间隔(秒)
        """
        current_size = len(self.buffers.get(buffer_key, []))
        optimal_batch_size = self.calculate_optimal_batch_size(buffer_key)

        if current_size >= optimal_batch_size:
            return 0  # 立即刷新

        # 基于当前缓冲区大小动态计算
        fill_ratio = current_size / optimal_batch_size if optimal_batch_size > 0 else 0
        interval = self.max_flush_interval * (1 - fill_ratio)

        return max(self.min_flush_interval, interval)

    async def add_item(self, buffer_key: str, item: Dict[str, Any]):
        """
        添加项到缓冲区(智能刷新)

        Args:
            buffer_key: 缓冲区键
            item: 要添加的项
        """
        if buffer_key not in self.buffers:
            self.buffers[buffer_key] = []
            self.metrics[buffer_key] = {
                'total_items': 0,
                'total_flushes': 0,
                'avg_flush_time_ms': 0,
                'last_flush_time': time.time()
            }

        self.buffers[buffer_key].append(item)
        self.metrics[buffer_key]['total_items'] += 1

        # 计算最优批量大小
        optimal_batch_size = self.calculate_optimal_batch_size(buffer_key)
        current_size = len(self.buffers[buffer_key])

        # 达到最优批量大小时立即刷新
        if current_size >= optimal_batch_size:
            asyncio.create_task(self._flush_buffer_with_metrics(buffer_key))
        else:
            # 根据当前填充率动态调度刷新
            interval = self.calculate_optimal_flush_interval(buffer_key)
            asyncio.create_task(self._delayed_flush(buffer_key, interval))

    async def _delayed_flush(self, buffer_key: str, delay: float):
        """
        延迟刷新

        Args:
            buffer_key: 缓冲区键
            delay: 延迟时间(秒)
        """
        await asyncio.sleep(delay)

        # 再次检查是否需要刷新
        if buffer_key in self.buffers and len(self.buffers[buffer_key]) > 0:
            await self._flush_buffer_with_metrics(buffer_key)

    async def _flush_buffer_with_metrics(self, buffer_key: str):
        """
        带性能指标的缓冲区刷新

        Args:
            buffer_key: 缓冲区键
        """
        items = self.buffers.get(buffer_key, [])
        if not items or not self.flush_callback:
            return

        start_time = time.time()

        try:
            await self.flush_callback(buffer_key, items)

            # 更新性能指标
            flush_time_ms = int((time.time() - start_time) * 1000)
            metrics = self.metrics[buffer_key]
            metrics['total_flushes'] += 1
            metrics['last_flush_time'] = time.time()

            # 计算平均刷新时间(指数移动平均)
            alpha = 0.3
            metrics['avg_flush_time_ms'] = int(
                alpha * flush_time_ms +
                (1 - alpha) * metrics.get('avg_flush_time_ms', flush_time_ms)
            )

            # 清空缓冲区
            self.buffers[buffer_key] = []

            logger.debug(
                f"缓冲区刷新完成: {buffer_key}, "
                f"数量={len(items)}, 耗时={flush_time_ms}ms"
            )

        except Exception as e:
            logger.error(f"缓冲区刷新失败: {buffer_key}, 错误={e}")
            # 失败时不清空缓冲区,等待下次重试

    def set_flush_callback(self, callback: Callable):
        """
        设置刷新回调函数

        Args:
            callback: 刷新回调函数,签名为 async def callback(buffer_key: str, items: list)
        """
        self.flush_callback = callback

    def update_active_streams(self, count: int):
        """
        更新活跃流数量

        Args:
            count: 活跃流数量
        """
        self.active_streams = count
        logger.debug(f"更新活跃流数量: {count}")

    def get_performance_stats(self) -> Dict[str, Any]:
        """
        获取性能统计

        Returns:
            性能统计字典
        """
        buffer_stats = {}
        for buffer_key, metrics in self.metrics.items():
            buffer_stats[buffer_key] = {
                'current_size': len(self.buffers.get(buffer_key, [])),
                'total_items': metrics['total_items'],
                'total_flushes': metrics['total_flushes'],
                'avg_flush_time_ms': metrics['avg_flush_time_ms'],
                'optimal_batch_size': self.calculate_optimal_batch_size(buffer_key)
            }

        return {
            'system_metrics': {
                'cpu_usage': self.cpu_usage,
                'memory_usage': self.memory_usage,
                'active_streams': self.active_streams
            },
            'buffer_stats': buffer_stats
        }

    async def force_flush_all(self):
        """强制刷新所有缓冲区"""
        logger.info("强制刷新所有缓冲区")
        flush_tasks = []
        for buffer_key in list(self.buffers.keys()):
            if len(self.buffers[buffer_key]) > 0:
                flush_tasks.append(self._flush_buffer_with_metrics(buffer_key))

        if flush_tasks:
            await asyncio.gather(*flush_tasks, return_exceptions=True)

    def clear_all_buffers(self):
        """清空所有缓冲区(不刷新)"""
        self.buffers.clear()
        logger.info("已清空所有缓冲区")
