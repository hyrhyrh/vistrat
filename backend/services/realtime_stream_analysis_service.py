"""
实时流AI分析服务 - 专门处理RTSP实时流
基于统一分析引擎，添加实时流特有的管理功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from services.unified_analysis_engine import unified_analysis_engine, UnifiedAnalysisTask
from services.video_analysis_template_service import video_analysis_template_service
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


@dataclass
class RealtimeStreamConfig:
    """实时流配置"""
    stream_id: str
    stream_name: str
    rtsp_url: str
    template_ids: List[str]
    frame_interval: float = 3.0  # 采样间隔（秒）
    auto_restart: bool = True    # 自动重启
    max_reconnect_attempts: int = 5
    
    # 高级配置
    analysis_enabled: bool = True
    alert_enabled: bool = True
    storage_enabled: bool = True
    
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = now()
        if self.updated_at is None:
            self.updated_at = now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        data['updated_at'] = self.updated_at.isoformat() if self.updated_at else None
        return data


@dataclass
class RealtimeStreamStatus:
    """实时流状态"""
    stream_id: str
    status: str  # 'stopped', 'starting', 'running', 'error', 'reconnecting'
    task_id: Optional[str] = None
    
    # 统计信息
    frames_processed: int = 0
    alerts_generated: int = 0
    connection_uptime: float = 0  # 连接持续时间（秒）
    last_frame_time: Optional[datetime] = None
    
    # 错误信息
    error_message: Optional[str] = None
    reconnect_count: int = 0
    
    # 时间戳
    started_at: Optional[datetime] = None
    last_updated: datetime = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['last_frame_time'] = self.last_frame_time.isoformat() if self.last_frame_time else None
        data['last_updated'] = self.last_updated.isoformat() if self.last_updated else None
        return data


class RealtimeStreamAnalysisService:
    """
    实时流AI分析服务
    管理多个实时流的AI分析任务
    """
    
    def __init__(self):
        # 流配置存储
        self.stream_configs: Dict[str, RealtimeStreamConfig] = {}
        self.stream_statuses: Dict[str, RealtimeStreamStatus] = {}
        
        # 任务管理
        self.active_tasks: Dict[str, str] = {}  # stream_id -> task_id
        
        # 监控任务
        self.monitor_task = None
        self.is_monitoring = False
        
        # 延迟启动监控服务
        self._monitoring_started = False
    
    def _start_monitoring(self):
        """启动后台监控服务"""
        if self._monitoring_started:
            return
        
        try:
            # 检查是否有运行的事件循环
            loop = asyncio.get_running_loop()
            if self.monitor_task is None or self.monitor_task.done():
                self.monitor_task = asyncio.create_task(self._monitor_streams())
                self._monitoring_started = True
        except RuntimeError:
            # 没有运行的事件循环，稍后再启动
            logger.debug("No running event loop, monitoring will start later")
            pass
    
    async def create_stream_config(self, stream_name: str, rtsp_url: str, 
                                 template_ids: List[str], **kwargs) -> str:
        """
        创建实时流配置
        
        Args:
            stream_name: 流名称
            rtsp_url: RTSP地址
            template_ids: AI算法模板ID列表
            **kwargs: 其他配置参数
        
        Returns:
            stream_id: 生成的流ID
        """
        # 确保监控服务已启动
        self._start_monitoring()
        
        try:
            # 生成唯一流ID
            import uuid
            stream_id = f"stream_{int(now().timestamp())}_{str(uuid.uuid4())[:8]}"
            
            # 验证模板ID
            if not template_ids:
                raise ValueError("必须指定至少一个AI分析算法")
            
            # TODO(stream_analysis): 验证模板ID是否存在，调用 _validate_templates 方法
            
            # 创建流配置
            config = RealtimeStreamConfig(
                stream_id=stream_id,
                stream_name=stream_name,
                rtsp_url=rtsp_url,
                template_ids=template_ids,
                frame_interval=kwargs.get('frame_interval', 3.0),
                auto_restart=kwargs.get('auto_restart', True),
                max_reconnect_attempts=kwargs.get('max_reconnect_attempts', 5),
                analysis_enabled=kwargs.get('analysis_enabled', True),
                alert_enabled=kwargs.get('alert_enabled', True),
                storage_enabled=kwargs.get('storage_enabled', True)
            )
            
            # 存储配置
            self.stream_configs[stream_id] = config
            
            # 初始化状态
            self.stream_statuses[stream_id] = RealtimeStreamStatus(
                stream_id=stream_id,
                status='stopped'
            )
            
            logger.info(f"创建实时流配置: {stream_id}, 名称: {stream_name}, URL: {rtsp_url}")
            
            return stream_id
            
        except Exception as e:
            logger.error(f"创建实时流配置失败: {e}")
            raise
    
    async def start_stream_analysis(self, stream_id: str) -> Dict[str, Any]:
        """启动实时流分析"""
        try:
            if stream_id not in self.stream_configs:
                raise ValueError(f"实时流配置不存在: {stream_id}")
            
            config = self.stream_configs[stream_id]
            status = self.stream_statuses[stream_id]
            
            # 检查是否已在运行
            if status.status == 'running':
                return {
                    'success': False,
                    'message': '实时流分析已在运行',
                    'stream_id': stream_id,
                    'task_id': status.task_id
                }
            
            # 更新状态
            status.status = 'starting'
            status.started_at = now()
            status.error_message = None
            status.last_updated = now()
            
            logger.info(f"启动实时流分析: {stream_id}")
            
            # 启动统一分析引擎
            result = await unified_analysis_engine.start_analysis(
                source_type='rtsp_stream',
                source_path=config.rtsp_url,
                source_id=stream_id,
                template_ids=config.template_ids,
                analysis_config={
                    'frame_interval': config.frame_interval,
                    'auto_restart': config.auto_restart,
                    'max_reconnect_attempts': config.max_reconnect_attempts
                }
            )
            
            # 更新状态
            status.task_id = result['task_id']
            status.status = 'running'
            self.active_tasks[stream_id] = result['task_id']
            
            logger.info(f"实时流分析已启动: {stream_id}, 任务ID: {result['task_id']}")
            
            return {
                'success': True,
                'message': '实时流分析已启动',
                'stream_id': stream_id,
                'task_id': result['task_id'],
                'config': config.to_dict()
            }
            
        except Exception as e:
            logger.error(f"启动实时流分析失败 {stream_id}: {e}")
            
            # 更新错误状态
            if stream_id in self.stream_statuses:
                self.stream_statuses[stream_id].status = 'error'
                self.stream_statuses[stream_id].error_message = str(e)
                self.stream_statuses[stream_id].last_updated = now()
            
            raise
    
    async def stop_stream_analysis(self, stream_id: str) -> Dict[str, Any]:
        """停止实时流分析"""
        try:
            if stream_id not in self.stream_configs:
                raise ValueError(f"实时流配置不存在: {stream_id}")
            
            status = self.stream_statuses[stream_id]
            
            # 检查是否在运行
            if status.status != 'running':
                return {
                    'success': False,
                    'message': '实时流分析未在运行',
                    'stream_id': stream_id
                }
            
            # 停止分析任务
            if status.task_id:
                await unified_analysis_engine.stop_analysis(status.task_id)
            
            # 更新状态
            status.status = 'stopped'
            status.task_id = None
            status.last_updated = now()
            
            # 清理活跃任务
            if stream_id in self.active_tasks:
                del self.active_tasks[stream_id]
            
            logger.info(f"实时流分析已停止: {stream_id}")
            
            return {
                'success': True,
                'message': '实时流分析已停止',
                'stream_id': stream_id
            }
            
        except Exception as e:
            logger.error(f"停止实时流分析失败 {stream_id}: {e}")
            raise
    
    async def get_stream_status(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """获取实时流状态"""
        if stream_id not in self.stream_configs:
            return None
        
        config = self.stream_configs[stream_id]
        status = self.stream_statuses[stream_id]
        
        # 获取任务详细状态
        task_status = None
        if status.task_id:
            task_status = await unified_analysis_engine.get_task_status(status.task_id)
        
        return {
            'stream_id': stream_id,
            'config': config.to_dict(),
            'status': status.to_dict(),
            'task_status': task_status
        }
    
    async def list_streams(self) -> List[Dict[str, Any]]:
        """列出所有实时流"""
        streams = []
        
        for stream_id in self.stream_configs:
            stream_info = await self.get_stream_status(stream_id)
            if stream_info:
                streams.append(stream_info)
        
        return streams
    
    async def update_stream_config(self, stream_id: str, **updates) -> bool:
        """更新实时流配置"""
        try:
            if stream_id not in self.stream_configs:
                raise ValueError(f"实时流配置不存在: {stream_id}")
            
            config = self.stream_configs[stream_id]
            status = self.stream_statuses[stream_id]
            
            # 检查是否需要重启
            restart_required = False
            critical_fields = ['rtsp_url', 'template_ids', 'frame_interval']
            
            for field in critical_fields:
                if field in updates and getattr(config, field, None) != updates[field]:
                    restart_required = True
                    break
            
            # 更新配置
            for key, value in updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            config.updated_at = now()
            
            # 如果在运行且需要重启
            if restart_required and status.status == 'running':
                logger.info(f"配置变更需要重启流分析: {stream_id}")
                await self.stop_stream_analysis(stream_id)
                await asyncio.sleep(1)  # 等待停止完成
                await self.start_stream_analysis(stream_id)
            
            logger.info(f"实时流配置已更新: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新实时流配置失败 {stream_id}: {e}")
            return False
    
    async def delete_stream_config(self, stream_id: str) -> bool:
        """删除实时流配置"""
        try:
            if stream_id not in self.stream_configs:
                return False
            
            # 先停止分析
            if self.stream_statuses[stream_id].status == 'running':
                await self.stop_stream_analysis(stream_id)
            
            # 删除配置和状态
            del self.stream_configs[stream_id]
            del self.stream_statuses[stream_id]
            
            if stream_id in self.active_tasks:
                del self.active_tasks[stream_id]
            
            logger.info(f"实时流配置已删除: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除实时流配置失败 {stream_id}: {e}")
            return False
    
    async def _monitor_streams(self):
        """后台监控所有实时流"""
        logger.info("实时流监控服务已启动")
        self.is_monitoring = True
        
        while self.is_monitoring:
            try:
                current_time = now()
                
                for stream_id, status in self.stream_statuses.items():
                    if status.status == 'running' and status.task_id:
                        # 获取最新任务状态
                        task_status = await unified_analysis_engine.get_task_status(status.task_id)
                        
                        if task_status:
                            # 更新统计信息
                            status.frames_processed = task_status.get('frames_processed', 0)
                            status.alerts_generated = task_status.get('alerts_generated', 0)
                            
                            if task_status.get('last_frame_time'):
                                status.last_frame_time = datetime.fromisoformat(
                                    task_status['last_frame_time'].replace('Z', '+00:00')
                                )
                            
                            # 计算连接时长
                            if status.started_at:
                                status.connection_uptime = (current_time - status.started_at).total_seconds()
                            
                            # 检查任务状态
                            task_current_status = task_status.get('status', 'unknown')
                            
                            if task_current_status == 'failed':
                                status.status = 'error'
                                status.error_message = task_status.get('error_message', '未知错误')
                                logger.warning(f"检测到流分析失败: {stream_id}")
                                
                                # 自动重启
                                config = self.stream_configs.get(stream_id)
                                if config and config.auto_restart:
                                    logger.info(f"自动重启流分析: {stream_id}")
                                    await asyncio.sleep(5)  # 等待5秒后重启
                                    await self.start_stream_analysis(stream_id)
                            
                            elif task_current_status == 'cancelled':
                                status.status = 'stopped'
                                status.task_id = None
                        else:
                            # 任务不存在，可能已被清理
                            status.status = 'error'
                            status.error_message = '分析任务丢失'
                        
                        status.last_updated = current_time
                
                # 每10秒检查一次
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"流监控异常: {e}")
                await asyncio.sleep(5)
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        stats = {
            'total_streams': len(self.stream_configs),
            'running_streams': 0,
            'stopped_streams': 0,
            'error_streams': 0,
            'total_frames_processed': 0,
            'total_alerts_generated': 0,
            'engine_stats': unified_analysis_engine.get_engine_stats()
        }
        
        for status in self.stream_statuses.values():
            if status.status == 'running':
                stats['running_streams'] += 1
            elif status.status == 'stopped':
                stats['stopped_streams'] += 1
            elif status.status == 'error':
                stats['error_streams'] += 1
            
            stats['total_frames_processed'] += status.frames_processed
            stats['total_alerts_generated'] += status.alerts_generated
        
        return stats
    
    async def shutdown(self):
        """关闭服务"""
        logger.info("正在关闭实时流分析服务...")
        
        self.is_monitoring = False
        
        # 停止所有运行中的流
        for stream_id in list(self.active_tasks.keys()):
            try:
                await self.stop_stream_analysis(stream_id)
            except Exception as e:
                logger.error(f"停止流分析失败 {stream_id}: {e}")
        
        # 等待监控任务结束
        if self.monitor_task and not self.monitor_task.done():
            try:
                await asyncio.wait_for(self.monitor_task, timeout=5.0)
            except asyncio.TimeoutError:
                self.monitor_task.cancel()
        
        logger.info("实时流分析服务已关闭")


# 创建全局实例
realtime_stream_service = RealtimeStreamAnalysisService()