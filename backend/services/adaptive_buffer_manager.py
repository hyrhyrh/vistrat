"""
自适应缓冲区管理器
动态调整缓冲区刷新策略，降低数据延迟
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict
from config.settings import VideoConfig

logger = logging.getLogger(__name__)


@dataclass
class BufferMetrics:
    """缓冲区性能指标"""
    size: int = 0
    last_flush_time: float = 0.0
    flush_count: int = 0
    total_items_processed: int = 0
    avg_flush_size: float = 0.0
    peak_size: int = 0
    
    def update_flush_metrics(self, items_count: int):
        """更新刷新指标"""
        self.flush_count += 1
        self.total_items_processed += items_count
        self.avg_flush_size = self.total_items_processed / self.flush_count
        self.last_flush_time = time.time()
        if items_count > self.peak_size:
            self.peak_size = items_count


class AdaptiveBufferManager:
    """自适应缓冲区管理器"""
    
    def __init__(self):
        self.buffers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.metrics: Dict[str, BufferMetrics] = defaultdict(BufferMetrics)
        
        # 动态配置参数
        self.base_flush_interval = VideoConfig.STREAM_BUFFER_FLUSH_INTERVAL
        self.base_batch_size = VideoConfig.STREAM_BUFFER_BATCH_SIZE
        self.min_flush_interval = 3  # 最小刷新间隔3秒
        self.max_flush_interval = 60  # 最大刷新间隔60秒
        self.emergency_threshold = self.base_batch_size * 1.5  # 紧急阈值 - 优化: 降低触发频率
        
        # 系统负载监控
        self.system_load = 0.0
        self.active_streams = 0
        self.recent_flush_times = []  # 记录最近的刷新耗时
        
        self.is_running = False
        self.flush_callback = None
        
        logger.info(f"自适应缓冲区管理器已初始化: 基础间隔={self.base_flush_interval}s, 基础批量={self.base_batch_size}")
    
    def set_flush_callback(self, callback):
        """设置刷新回调函数"""
        self.flush_callback = callback
    
    def add_item(self, buffer_key: str, item: Dict[str, Any]):
        """添加项目到缓冲区"""
        self.buffers[buffer_key].append(item)
        self.metrics[buffer_key].size = len(self.buffers[buffer_key])
        
        # 检查是否需要紧急刷新
        if self.metrics[buffer_key].size >= self.emergency_threshold:
            logger.warning(f"缓冲区 {buffer_key} 达到紧急阈值 {self.emergency_threshold}，触发紧急刷新")
            asyncio.create_task(self._emergency_flush(buffer_key))
    
    def get_buffer_metrics(self, buffer_key: str) -> BufferMetrics:
        """获取缓冲区指标"""
        return self.metrics[buffer_key]
    
    def get_all_metrics(self) -> Dict[str, BufferMetrics]:
        """获取所有缓冲区指标"""
        return dict(self.metrics)
    
    def update_system_load(self, active_streams: int):
        """更新系统负载信息"""
        self.active_streams = active_streams
        # 简单的负载计算：基于活跃流数量
        self.system_load = min(active_streams / VideoConfig.MAX_CONCURRENT_STREAMS, 1.0)
    
    def _calculate_dynamic_flush_interval(self, buffer_key: str) -> int:
        """计算动态刷新间隔"""
        metrics = self.metrics[buffer_key]
        
        # 基于缓冲区大小的调整因子
        size_factor = 1.0
        if metrics.size > self.base_batch_size:
            size_factor = 0.5  # 缓冲区大时，减少间隔
        elif metrics.size < self.base_batch_size // 2:
            size_factor = 1.5  # 缓冲区小时，增加间隔
        
        # 基于系统负载的调整因子
        load_factor = 1.0
        if self.system_load > 0.8:
            load_factor = 1.3  # 高负载时，适当增加间隔
        elif self.system_load < 0.3:
            load_factor = 0.8  # 低负载时，减少间隔
        
        # 基于历史刷新性能的调整
        performance_factor = 1.0
        if len(self.recent_flush_times) > 0:
            avg_flush_time = sum(self.recent_flush_times) / len(self.recent_flush_times)
            if avg_flush_time > 2.0:  # 刷新耗时超过2秒
                performance_factor = 1.2
            elif avg_flush_time < 0.5:  # 刷新很快
                performance_factor = 0.9
        
        # 计算最终间隔
        interval = int(self.base_flush_interval * size_factor * load_factor * performance_factor)
        return max(self.min_flush_interval, min(interval, self.max_flush_interval))
    
    def _calculate_dynamic_batch_size(self, buffer_key: str) -> int:
        """计算动态批量大小"""
        metrics = self.metrics[buffer_key]
        
        # 基于平均刷新大小调整
        if metrics.avg_flush_size > 0:
            if metrics.avg_flush_size > self.base_batch_size * 1.5:
                return int(self.base_batch_size * 1.2)  # 增加批量大小
            elif metrics.avg_flush_size < self.base_batch_size * 0.5:
                return int(self.base_batch_size * 0.8)  # 减少批量大小
        
        return self.base_batch_size
    
    async def _emergency_flush(self, buffer_key: str):
        """紧急刷新指定缓冲区"""
        if buffer_key in self.buffers and self.buffers[buffer_key]:
            start_time = time.time()
            items = self.buffers[buffer_key][:]
            self.buffers[buffer_key].clear()
            
            if self.flush_callback:
                try:
                    await self.flush_callback(buffer_key, items)
                    
                    # 更新指标
                    self.metrics[buffer_key].update_flush_metrics(len(items))
                    self.metrics[buffer_key].size = 0
                    
                    flush_time = time.time() - start_time
                    self._record_flush_time(flush_time)
                    
                    logger.info(f"紧急刷新完成: {buffer_key}, 处理 {len(items)} 项, 耗时 {flush_time:.2f}s")
                    
                except Exception as e:
                    logger.error(f"紧急刷新失败: {buffer_key}, 错误: {e}")
                    # 刷新失败，将数据放回缓冲区
                    self.buffers[buffer_key].extend(items)
    
    def _record_flush_time(self, flush_time: float):
        """记录刷新耗时"""
        self.recent_flush_times.append(flush_time)
        # 只保留最近10次的记录
        if len(self.recent_flush_times) > 10:
            self.recent_flush_times.pop(0)
    
    async def start_adaptive_flushing(self):
        """启动自适应刷新"""
        if self.is_running:
            return
        
        self.is_running = True
        logger.info("自适应缓冲区刷新已启动")
        
        while self.is_running:
            try:
                # 为每个缓冲区计算动态参数
                flush_tasks = []
                
                for buffer_key in list(self.buffers.keys()):
                    metrics = self.metrics[buffer_key]
                    buffer_size = len(self.buffers[buffer_key])
                    
                    if buffer_size == 0:
                        continue
                    
                    # 计算动态参数
                    dynamic_interval = self._calculate_dynamic_flush_interval(buffer_key)
                    dynamic_batch_size = self._calculate_dynamic_batch_size(buffer_key)
                    
                    # 判断是否需要刷新
                    time_since_last_flush = time.time() - metrics.last_flush_time
                    should_flush = False
                    flush_reason = ""
                    
                    if buffer_size >= dynamic_batch_size:
                        should_flush = True
                        flush_reason = f"大小阈值({dynamic_batch_size})"
                    elif time_since_last_flush >= dynamic_interval:
                        should_flush = True
                        flush_reason = f"时间阈值({dynamic_interval}s)"
                    elif buffer_size >= self.emergency_threshold:
                        should_flush = True
                        flush_reason = f"紧急阈值({self.emergency_threshold})"
                    
                    if should_flush:
                        logger.debug(f"触发缓冲区刷新: {buffer_key}, 原因: {flush_reason}, 大小: {buffer_size}")
                        flush_tasks.append(self._flush_buffer(buffer_key))
                
                # 并发执行刷新任务
                if flush_tasks:
                    await asyncio.gather(*flush_tasks, return_exceptions=True)
                
                # 动态调整检查间隔
                check_interval = min(self.base_flush_interval // 2, 5)
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"自适应刷新循环异常: {e}")
                await asyncio.sleep(5)
    
    async def _flush_buffer(self, buffer_key: str):
        """刷新指定缓冲区"""
        if buffer_key not in self.buffers or not self.buffers[buffer_key]:
            return
        
        start_time = time.time()
        items = self.buffers[buffer_key][:]
        self.buffers[buffer_key].clear()
        
        if self.flush_callback:
            try:
                await self.flush_callback(buffer_key, items)
                
                # 更新指标
                self.metrics[buffer_key].update_flush_metrics(len(items))
                self.metrics[buffer_key].size = 0
                
                flush_time = time.time() - start_time
                self._record_flush_time(flush_time)
                
                logger.debug(f"缓冲区刷新完成: {buffer_key}, 处理 {len(items)} 项, 耗时 {flush_time:.2f}s")
                
            except Exception as e:
                logger.error(f"缓冲区刷新失败: {buffer_key}, 错误: {e}")
                # 刷新失败，将数据放回缓冲区
                self.buffers[buffer_key].extend(items)
    
    async def stop(self):
        """停止自适应刷新"""
        self.is_running = False
        
        # 最后刷新所有缓冲区
        for buffer_key in list(self.buffers.keys()):
            if self.buffers[buffer_key]:
                await self._flush_buffer(buffer_key)
        
        logger.info("自适应缓冲区管理器已停止")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        total_processed = sum(m.total_items_processed for m in self.metrics.values())
        total_flushes = sum(m.flush_count for m in self.metrics.values())
        
        stats = {
            "total_buffers": len(self.buffers),
            "total_items_processed": total_processed,
            "total_flushes": total_flushes,
            "avg_flush_size": total_processed / max(total_flushes, 1),
            "system_load": self.system_load,
            "active_streams": self.active_streams,
            "avg_flush_time": sum(self.recent_flush_times) / max(len(self.recent_flush_times), 1),
            "buffer_details": {}
        }
        
        for key, metrics in self.metrics.items():
            stats["buffer_details"][key] = {
                "current_size": metrics.size,
                "peak_size": metrics.peak_size,
                "flush_count": metrics.flush_count,
                "total_processed": metrics.total_items_processed,
                "avg_flush_size": metrics.avg_flush_size,
                "last_flush_ago": time.time() - metrics.last_flush_time
            }
        
        return stats


# 创建全局实例
adaptive_buffer_manager = AdaptiveBufferManager()