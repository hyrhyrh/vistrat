"""
性能指标监控系统
建立完整的系统性能监控体系
优化方案9: 性能指标监控
"""

import asyncio
import time
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """系统指标"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    disk_usage_percent: float
    network_sent_mb: float
    network_recv_mb: float


@dataclass
class ServiceMetrics:
    """服务指标"""
    timestamp: float
    active_streams: int
    active_tasks: int
    frames_per_second: float
    alerts_per_minute: float
    ai_avg_response_time_ms: float
    buffer_size: int
    elasticsearch_latency_ms: float


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self.system_metrics_history: List[SystemMetrics] = []
        self.service_metrics_history: List[ServiceMetrics] = []
        self.max_history_size = 1000  # 保留最近1000条

        # 监控任务
        self._collection_task = None
        self._running = False

        # 用于计算服务指标的缓存
        self._last_frame_count = 0
        self._last_alert_count = 0
        self._ai_response_times = []  # 最近的AI响应时间

    async def start(self):
        """启动指标收集器"""
        if self._running:
            logger.warning("指标收集器已在运行")
            return

        self._running = True
        self._collection_task = asyncio.create_task(self._collection_loop())
        logger.info("✅ 性能指标监控系统已启动")

    async def stop(self):
        """停止指标收集器"""
        self._running = False
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 性能指标监控系统已停止")

    async def _collection_loop(self):
        """指标收集循环"""
        while self._running:
            try:
                # 收集系统指标
                system_metrics = self._collect_system_metrics()
                if system_metrics:
                    self.system_metrics_history.append(system_metrics)

                # 收集服务指标
                service_metrics = await self._collect_service_metrics()
                if service_metrics:
                    self.service_metrics_history.append(service_metrics)

                # 限制历史记录大小
                if len(self.system_metrics_history) > self.max_history_size:
                    self.system_metrics_history = self.system_metrics_history[-self.max_history_size:]

                if len(self.service_metrics_history) > self.max_history_size:
                    self.service_metrics_history = self.service_metrics_history[-self.max_history_size:]

                # 检查告警条件
                if system_metrics and service_metrics:
                    await self._check_alerts(system_metrics, service_metrics)

            except Exception as e:
                logger.error(f"指标收集失败: {e}", exc_info=True)

            # 每10秒收集一次
            await asyncio.sleep(10)

    def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """收集系统指标"""
        try:
            import psutil
        except ImportError:
            logger.warning("psutil未安装,无法收集系统指标")
            return None

        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()

            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(interval=0.1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                disk_usage_percent=disk.percent,
                network_sent_mb=network.bytes_sent / (1024 * 1024),
                network_recv_mb=network.bytes_recv / (1024 * 1024)
            )
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return None

    async def _collect_service_metrics(self) -> Optional[ServiceMetrics]:
        """收集服务指标"""
        try:
            # 动态导入避免循环依赖
            from services.stream_frame_analyzer import stream_frame_analyzer

            # 🔧 修复：使用新的多流架构获取活跃流数量
            active_streams = len(stream_frame_analyzer.analyzing_streams)

            # 计算帧率(最近1分钟)
            recent_metrics = self.service_metrics_history[-6:]  # 最近60秒
            if recent_metrics:
                total_frames = sum(m.frames_per_second for m in recent_metrics)
                fps = total_frames / len(recent_metrics)
            else:
                fps = 0.0

            # 计算AI平均响应时间
            if self._ai_response_times:
                avg_ai_time = sum(self._ai_response_times) / len(self._ai_response_times)
                # 只保留最近100条
                self._ai_response_times = self._ai_response_times[-100:]
            else:
                avg_ai_time = 0.0

            # 获取缓冲区大小(如果有缓冲区管理器)
            buffer_size = 0
            try:
                from services.enhanced_adaptive_buffer_manager import enhanced_buffer_manager
                buffer_stats = enhanced_buffer_manager.get_performance_stats()
                buffer_size = sum(
                    stats['current_size']
                    for stats in buffer_stats.get('buffer_stats', {}).values()
                )
            except (ImportError, Exception):
                pass

            return ServiceMetrics(
                timestamp=time.time(),
                active_streams=active_streams,
                active_tasks=active_streams,  # 简化:假设每个流一个任务
                frames_per_second=fps,
                alerts_per_minute=0.0,  # 待实现
                ai_avg_response_time_ms=avg_ai_time,
                buffer_size=buffer_size,
                elasticsearch_latency_ms=0.0  # 待实现
            )
        except Exception as e:
            logger.error(f"收集服务指标失败: {e}", exc_info=True)
            return None

    async def _check_alerts(self, system: SystemMetrics, service: ServiceMetrics):
        """检查告警条件"""
        alerts = []

        # CPU告警（已禁用 - 用户要求关闭此告警推送）
        # if system.cpu_percent > 95:
        #     alerts.append({
        #         'type': 'HIGH_CPU_USAGE',
        #         'severity': 'critical',
        #         'message': f'CPU使用率过高: {system.cpu_percent:.1f}%'
        #     })

        # 内存告警
        if system.memory_percent > 85:
            alerts.append({
                'type': 'HIGH_MEMORY_USAGE',
                'severity': 'warning',
                'message': f'内存使用率过高: {system.memory_percent:.1f}%'
            })

        # 缓冲区告警
        if service.buffer_size > 500:
            alerts.append({
                'type': 'LARGE_BUFFER_SIZE',
                'severity': 'warning',
                'message': f'缓冲区积压过多: {service.buffer_size}条记录'
            })

        # AI响应时间告警
        if service.ai_avg_response_time_ms > 5000:
            alerts.append({
                'type': 'SLOW_AI_RESPONSE',
                'severity': 'warning',
                'message': f'AI响应时间过长: {service.ai_avg_response_time_ms:.0f}ms'
            })

        # 发送告警
        for alert in alerts:
            await self._send_alert(alert)

    async def _send_alert(self, alert: Dict):
        """发送告警"""
        logger.warning(f"⚠️ 性能告警: [{alert['severity'].upper()}] {alert['message']}")

        # 发送到告警通知服务
        try:
            # 动态导入避免循环依赖
            from services.alert_notification_service import (
                alert_notification_service,
                AlertRecord,
                NotificationSeverity
            )

            # 映射严重级别
            severity_map = {
                'info': NotificationSeverity.INFO,
                'warning': NotificationSeverity.WARNING,
                'error': NotificationSeverity.ERROR,
                'critical': NotificationSeverity.CRITICAL
            }

            severity = severity_map.get(alert['severity'], NotificationSeverity.WARNING)

            # 创建告警记录
            alert_record = AlertRecord(
                alert_type=alert['type'],
                severity=severity,
                message=alert['message'],
                timestamp=time.time(),
                source="性能监控系统"
            )

            # 记录告警(会根据级别决定是否即时发送)
            await alert_notification_service.record_alert(alert_record)

        except Exception as e:
            logger.error(f"发送告警到通知服务失败: {e}")

    def record_ai_response_time(self, response_time_ms: float):
        """
        记录AI响应时间

        Args:
            response_time_ms: AI响应时间(毫秒)
        """
        self._ai_response_times.append(response_time_ms)
        # 限制列表大小
        if len(self._ai_response_times) > 100:
            self._ai_response_times = self._ai_response_times[-100:]

    def get_latest_metrics(self) -> Dict[str, Any]:
        """获取最新指标"""
        if not self.system_metrics_history or not self.service_metrics_history:
            return {
                'system': {},
                'service': {},
                'status': 'no_data'
            }

        system = self.system_metrics_history[-1]
        service = self.service_metrics_history[-1]

        return {
            'system': {
                'cpu_percent': round(system.cpu_percent, 2),
                'memory_percent': round(system.memory_percent, 2),
                'memory_used_mb': round(system.memory_used_mb, 2),
                'disk_usage_percent': round(system.disk_usage_percent, 2),
                'network_sent_mb': round(system.network_sent_mb, 2),
                'network_recv_mb': round(system.network_recv_mb, 2)
            },
            'service': {
                'active_streams': service.active_streams,
                'active_tasks': service.active_tasks,
                'frames_per_second': round(service.frames_per_second, 2),
                'alerts_per_minute': round(service.alerts_per_minute, 2),
                'ai_avg_response_time_ms': round(service.ai_avg_response_time_ms, 2),
                'buffer_size': service.buffer_size,
                'elasticsearch_latency_ms': round(service.elasticsearch_latency_ms, 2)
            },
            'status': 'ok',
            'timestamp': time.time()
        }

    def get_metrics_history(self, duration_seconds: int = 600) -> Dict[str, List]:
        """
        获取历史指标

        Args:
            duration_seconds: 时间范围(秒),默认600秒(10分钟)

        Returns:
            历史指标字典
        """
        cutoff_time = time.time() - duration_seconds

        system_history = [
            m for m in self.system_metrics_history
            if m.timestamp >= cutoff_time
        ]

        service_history = [
            m for m in self.service_metrics_history
            if m.timestamp >= cutoff_time
        ]

        return {
            'system': [
                {
                    'timestamp': m.timestamp,
                    'cpu_percent': round(m.cpu_percent, 2),
                    'memory_percent': round(m.memory_percent, 2),
                    'memory_used_mb': round(m.memory_used_mb, 2)
                }
                for m in system_history
            ],
            'service': [
                {
                    'timestamp': m.timestamp,
                    'active_streams': m.active_streams,
                    'fps': round(m.frames_per_second, 2),
                    'buffer_size': m.buffer_size,
                    'ai_avg_response_time_ms': round(m.ai_avg_response_time_ms, 2)
                }
                for m in service_history
            ],
            'duration_seconds': duration_seconds,
            'data_points': {
                'system': len(system_history),
                'service': len(service_history)
            }
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """
        获取性能摘要

        Returns:
            性能摘要字典
        """
        if not self.system_metrics_history or not self.service_metrics_history:
            return {'status': 'no_data'}

        # 最近10分钟的数据
        recent_system = self.system_metrics_history[-60:]  # 10分钟
        recent_service = self.service_metrics_history[-60:]

        # 计算平均值
        avg_cpu = sum(m.cpu_percent for m in recent_system) / len(recent_system) if recent_system else 0
        avg_memory = sum(m.memory_percent for m in recent_system) / len(recent_system) if recent_system else 0
        avg_fps = sum(m.frames_per_second for m in recent_service) / len(recent_service) if recent_service else 0

        # 计算最大值
        max_cpu = max((m.cpu_percent for m in recent_system), default=0)
        max_memory = max((m.memory_percent for m in recent_system), default=0)
        max_buffer = max((m.buffer_size for m in recent_service), default=0)

        return {
            'status': 'ok',
            'period': '10分钟',
            'averages': {
                'cpu_percent': round(avg_cpu, 2),
                'memory_percent': round(avg_memory, 2),
                'frames_per_second': round(avg_fps, 2)
            },
            'peaks': {
                'cpu_percent': round(max_cpu, 2),
                'memory_percent': round(max_memory, 2),
                'buffer_size': max_buffer
            },
            'current': self.get_latest_metrics()
        }


# 创建全局实例
metrics_collector = MetricsCollector()
