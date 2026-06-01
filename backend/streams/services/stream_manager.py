"""
实时视频流管理服务
处理RTSP、WebRTC等实时视频流的接入和管理
"""

import asyncio
import cv2
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any

from models.video_metadata import VideoMetadata, VideoType, VideoStatus
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


class StreamManager:
    """实时视频流管理器"""
    
    def __init__(self, max_concurrent_streams: int = 10):
        self.max_concurrent_streams = max_concurrent_streams
        self._active_streams: Dict[str, VideoMetadata] = {}
        self._stream_handlers: Dict[str, Any] = {}
        self._frame_callbacks: Dict[str, List[Callable]] = {}
        # 🔧 ARM兼容：移除未使用的ThreadPoolExecutor
    
    async def create_stream(self, name: str, source_url: str, stream_type: VideoType,
                          username: Optional[str] = None, password: Optional[str] = None,
                          config: Optional[Dict] = None) -> VideoMetadata:
        """
        创建新的视频流
        
        Args:
            name: 流名称
            source_url: 流源地址
            stream_type: 流类型
            username: 认证用户名
            password: 认证密码
            config: 额外配置
            
        Returns:
            StreamMetadata: 流元数据
        """
        try:
            stream_config = config or {}
            
            # 创建流元数据
            stream = VideoMetadata(
                id=str(uuid.uuid4()),
                name=name,
                type=stream_type,
                source_path=source_url,
                description="",
                tags=[],
                status=VideoStatus.READY,
                created_at=now(),
                updated_at=now()
            )
            
            # 缓存流信息
            self._active_streams[stream.id] = stream
            
            logger.info(f"视频流已创建: {name} ({stream.id})")
            return stream
            
        except Exception as e:
            logger.error(f"创建视频流失败: {e}")
            raise
    
    async def start_stream(self, stream_id: str) -> bool:
        """启动视频流"""
        try:
            stream = self._active_streams.get(stream_id)
            if not stream:
                raise ValueError(f"流不存在: {stream_id}")
            
            if stream.is_active:
                logger.warning(f"流已经处于活跃状态: {stream_id}")
                return True
            
            # 根据流类型选择处理器
            if stream.type == VideoType.RTSP:
                handler = self.rtsp_handler
            elif stream.type == VideoType.WEBRTC:
                handler = self.webrtc_handler
            else:
                raise ValueError(f"不支持的流类型: {stream.type}")
            
            # 启动流处理
            success = await handler.start_stream(
                stream=stream,
                frame_callback=lambda frame, ts: self._on_frame_received(stream_id, frame, ts)
            )
            
            if success:
                stream.is_active = True
                stream.is_connected = True
                stream.connection_status = "connected"
                stream.connected_at = now()
                self._stream_handlers[stream_id] = handler
                
                logger.info(f"视频流已启动: {stream_id}")
                return True
            else:
                raise RuntimeError("流启动失败")
                
        except Exception as e:
            logger.error(f"启动视频流失败: {e}")
            return False
    
    async def stop_stream(self, stream_id: str) -> bool:
        """停止视频流"""
        try:
            stream = self._active_streams.get(stream_id)
            if not stream:
                return False
            
            # 停止流处理
            handler = self._stream_handlers.get(stream_id)
            if handler:
                await handler.stop_stream(stream_id)
                del self._stream_handlers[stream_id]
            
            # 更新状态
            stream.is_active = False
            stream.is_connected = False
            stream.connection_status = "disconnected"
            
            logger.info(f"视频流已停止: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止视频流失败: {e}")
            return False
    
    async def get_stream_list(self) -> List[VideoMetadata]:
        """获取所有活跃流列表"""
        return list(self._active_streams.values())
    
    async def get_stream_by_id(self, stream_id: str) -> Optional[VideoMetadata]:
        """根据ID获取流信息"""
        return self._active_streams.get(stream_id)
    
    async def update_stream_config(self, stream_id: str, config: Dict[str, Any]) -> bool:
        """更新流配置"""
        try:
            stream = self._active_streams.get(stream_id)
            if not stream:
                return False
            
            # 更新配置
            if 'enable_analysis' in config:
                stream.enable_analysis = config['enable_analysis']
            if 'analysis_interval' in config:
                stream.analysis_interval = config['analysis_interval']
            if 'prompt_template_ids' in config:
                stream.prompt_template_ids = config['prompt_template_ids']
            
            stream.updated_at = now()
            
            logger.info(f"流配置已更新: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新流配置失败: {e}")
            return False
    
    def add_frame_callback(self, stream_id: str, callback: Callable):
        """添加帧接收回调"""
        if stream_id not in self._frame_callbacks:
            self._frame_callbacks[stream_id] = []
        self._frame_callbacks[stream_id].append(callback)
    
    async def _validate_stream_connection(self, stream: VideoMetadata):
        """验证流连接"""
        try:
            if stream.type == VideoType.RTSP:
                # 尝试连接RTSP流
                cap = cv2.VideoCapture(stream.source_url)
                if not cap.isOpened():
                    raise ValueError("无法连接RTSP流")
                
                # 尝试读取一帧
                ret, frame = cap.read()
                if not ret:
                    raise ValueError("无法从RTSP流读取数据")
                
                # 更新流信息
                stream.fps = cap.get(cv2.CAP_PROP_FPS)
                stream.resolution = {
                    'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                }
                
                cap.release()
                
            elif stream.type == VideoType.CAMERA:
                # 验证摄像头设备
                device_id = int(stream.source_url) if stream.source_url.isdigit() else 0
                cap = cv2.VideoCapture(device_id)
                if not cap.isOpened():
                    raise ValueError("无法打开摄像头设备")
                cap.release()
            
            logger.info(f"流连接验证成功: {stream.source_url}")
            
        except Exception as e:
            logger.error(f"流连接验证失败: {e}")
            raise
    
    async def _on_frame_received(self, stream_id: str, frame, timestamp: float):
        """帧接收回调处理"""
        try:
            stream = self._active_streams.get(stream_id)
            if not stream:
                return
            
            # 更新统计信息
            stream.total_frames_received += 1
            stream.last_frame_time = now()
            
            # 调用注册的回调函数
            callbacks = self._frame_callbacks.get(stream_id, [])
            for callback in callbacks:
                try:
                    await callback(frame, timestamp, stream)
                except Exception as e:
                    logger.error(f"帧回调处理失败: {e}")
                    
        except Exception as e:
            logger.error(f"帧接收处理失败: {e}")
    
    async def get_stream_statistics(self, stream_id: str) -> Optional[Dict[str, Any]]:
        """获取流统计信息"""
        try:
            stream = self._active_streams.get(stream_id)
            if not stream:
                return None
            
            handler = self._stream_handlers.get(stream_id)
            handler_stats = await handler.get_statistics() if handler else {}
            
            return {
                "stream_info": stream.dict(),
                "handler_statistics": handler_stats,
                "uptime": (now() - stream.connected_at).total_seconds() if stream.connected_at else 0
            }
            
        except Exception as e:
            logger.error(f"获取流统计失败: {e}")
            return None