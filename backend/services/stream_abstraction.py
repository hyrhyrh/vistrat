"""
统一流抽象层 - Ultra深度设计
为本地视频和实时流提供统一的数据接口，使AI分析引擎完全复用
"""

import asyncio
import logging
import cv2
import numpy as np
from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


@dataclass
class StreamFrame:
    """统一的帧数据结构 - 屏蔽数据源差异"""
    frame_index: int
    timestamp: float  # 相对时间戳
    real_timestamp: datetime  # 绝对时间戳
    image_data: np.ndarray  # 标准化的图像数据
    source_id: str
    source_type: str  # 'video_file' | 'rtsp_stream'
    metadata: Dict[str, Any]
    
    def save_to_temp(self, temp_path: Path) -> str:
        """保存帧到临时文件，返回文件路径"""
        frame_filename = f"frame_{self.frame_index:06d}_{int(self.real_timestamp.timestamp())}.jpg"
        frame_path = temp_path / frame_filename
        cv2.imwrite(str(frame_path), self.image_data)
        return str(frame_path)


class StreamSource(ABC):
    """统一的数据源抽象接口"""
    
    def __init__(self, source_id: str, source_path: str):
        self.source_id = source_id
        self.source_path = source_path
        self.is_active = False
        self.metadata = {}
    
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化数据源"""
        pass
    
    @abstractmethod
    async def produce_frames(self, frame_interval: float = 5.0) -> AsyncIterator[StreamFrame]:
        """生产帧数据流 - 核心抽象方法"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict[str, Any]:
        """获取数据源信息"""
        pass


class VideoFileStream(StreamSource):
    """
    本地视频文件流 - 封装现有逻辑
    保持与原VideoAnalysisService完全兼容
    """
    
    def __init__(self, source_id: str, video_path: str):
        super().__init__(source_id, video_path)
        self.cap = None
        self.fps = 0
        self.total_frames = 0
        self.source_type = 'video_file'
    
    async def initialize(self) -> bool:
        """初始化视频文件"""
        try:
            # 处理MinIO路径的逻辑（从原代码移植）
            local_video_path = None
            video_path = self.source_path
            
            if video_path.startswith(('videos/', 'multi-videos/')):
                logger.info(f"检测到MinIO路径，需要下载: {video_path}")
                # 这里会在实际使用时通过dependency injection处理
                # 暂时使用原始路径
            
            self.cap = cv2.VideoCapture(video_path)
            if not self.cap.isOpened():
                logger.error(f"无法打开视频文件: {video_path}")
                return False
            
            self.fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            self.metadata = {
                'fps': self.fps,
                'total_frames': self.total_frames,
                'duration': self.total_frames / self.fps if self.fps > 0 else 0,
                'video_path': video_path
            }
            
            self.is_active = True
            logger.info(f"视频文件初始化成功: {self.total_frames} 帧, {self.fps} FPS")
            return True
            
        except Exception as e:
            logger.error(f"初始化视频文件失败: {e}")
            return False
    
    async def produce_frames(self, frame_interval: float = 5.0) -> AsyncIterator[StreamFrame]:
        """
        生产视频帧流 - 与原逻辑完全兼容
        frame_interval: 采样间隔（秒）
        """
        if not self.is_active or not self.cap:
            logger.error("视频流未初始化")
            return
        
        try:
            # 计算采样间隔（帧数）
            frame_skip = max(1, int(self.fps * frame_interval))
            
            frame_index = 0
            
            while self.is_active:
                ret, frame = self.cap.read()
                if not ret:
                    logger.info("视频文件读取完成")
                    break
                
                # 跳帧采样 - 与原逻辑完全一致
                if frame_index % frame_skip == 0:
                    timestamp = frame_index / self.fps
                    real_timestamp = now()
                    
                    stream_frame = StreamFrame(
                        frame_index=frame_index,
                        timestamp=timestamp,
                        real_timestamp=real_timestamp,
                        image_data=frame,
                        source_id=self.source_id,
                        source_type=self.source_type,
                        metadata={
                            'fps': self.fps,
                            'total_frames': self.total_frames,
                            'progress': frame_index / self.total_frames
                        }
                    )
                    
                    yield stream_frame
                
                frame_index += 1
                
                # 允许其他协程运行
                await asyncio.sleep(0)
            
        except Exception as e:
            logger.error(f"视频帧生产失败: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """清理视频资源"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_active = False
        logger.debug(f"视频流资源已清理: {self.source_id}")
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取视频文件信息"""
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'source_path': self.source_path,
            'fps': self.fps,
            'total_frames': self.total_frames,
            'duration': self.metadata.get('duration', 0),
            'is_active': self.is_active
        }


class RealtimeRTSPStream(StreamSource):
    """
    实时RTSP流 - 全新实现
    专门处理实时流的特殊需求
    """
    
    def __init__(self, source_id: str, rtsp_url: str, max_reconnect_attempts: int = 5):
        super().__init__(source_id, rtsp_url)
        self.rtsp_url = rtsp_url
        self.cap = None
        self.fps = 25.0  # 默认帧率
        self.source_type = 'rtsp_stream'
        
        # 实时流特有属性
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_count = 0
        self.last_frame_time = None
        self.connection_stable = False
        self.frame_buffer_size = 10  # 帧缓冲区大小
        
        # 性能监控
        self.frames_captured = 0
        self.frames_dropped = 0
        self.connection_start_time = None
    
    async def initialize(self) -> bool:
        """初始化RTSP流连接"""
        try:
            return await self._connect_stream()
        except Exception as e:
            logger.error(f"初始化RTSP流失败: {e}")
            return False
    
    async def _connect_stream(self) -> bool:
        """连接RTSP流，带重试机制"""
        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(f"尝试连接RTSP流 (第{attempt + 1}次): {self.rtsp_url}")
                
                # 优化的RTSP连接参数
                self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                
                # 设置缓冲区大小，减少延迟
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap.set(cv2.CAP_PROP_FPS, 25)
                
                if not self.cap.isOpened():
                    logger.warning(f"RTSP流连接失败，尝试重连 ({attempt + 1}/{self.max_reconnect_attempts})")
                    await asyncio.sleep(2 ** attempt)  # 指数退避
                    continue
                
                # 测试读取一帧
                ret, test_frame = self.cap.read()
                if not ret or test_frame is None:
                    logger.warning(f"RTSP流无法读取数据，尝试重连 ({attempt + 1}/{self.max_reconnect_attempts})")
                    self.cap.release()
                    await asyncio.sleep(2 ** attempt)
                    continue
                
                # 连接成功
                self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
                self.connection_stable = True
                self.connection_start_time = now()
                self.reconnect_count = 0
                
                self.metadata = {
                    'rtsp_url': self.rtsp_url,
                    'fps': self.fps,
                    'connection_time': self.connection_start_time.isoformat(),
                    'stream_type': 'realtime'
                }
                
                self.is_active = True
                logger.info(f"RTSP流连接成功: {self.rtsp_url}, FPS: {self.fps}")
                return True
                
            except Exception as e:
                logger.error(f"RTSP连接异常 (第{attempt + 1}次): {e}")
                if self.cap:
                    self.cap.release()
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"RTSP流连接彻底失败，已尝试 {self.max_reconnect_attempts} 次")
        return False
    
    async def produce_frames(self, frame_interval: float = 3.0) -> AsyncIterator[StreamFrame]:
        """
        生产实时帧流 - 持续不断的流处理
        frame_interval: 采样间隔（秒）
        """
        if not self.is_active or not self.cap:
            logger.error("RTSP流未初始化")
            return
        
        try:
            frame_index = 0
            last_sample_time = 0
            start_time = now()
            
            logger.info(f"开始RTSP实时帧采集，采样间隔: {frame_interval}秒")
            
            while self.is_active:
                try:
                    ret, frame = self.cap.read()
                    
                    if not ret or frame is None:
                        # 处理流中断
                        logger.warning("RTSP流数据中断，尝试重连")
                        self.connection_stable = False
                        
                        if await self._reconnect():
                            continue
                        else:
                            break
                    
                    self.frames_captured += 1
                    current_time = (now() - start_time).total_seconds()
                    
                    # 智能采样策略
                    if current_time - last_sample_time >= frame_interval:
                        real_timestamp = now()
                        
                        stream_frame = StreamFrame(
                            frame_index=frame_index,
                            timestamp=current_time,
                            real_timestamp=real_timestamp,
                            image_data=frame,
                            source_id=self.source_id,
                            source_type=self.source_type,
                            metadata={
                                'rtsp_url': self.rtsp_url,
                                'fps': self.fps,
                                'connection_stable': self.connection_stable,
                                'frames_captured': self.frames_captured,
                                'frames_dropped': self.frames_dropped,
                                'uptime': current_time
                            }
                        )
                        
                        yield stream_frame
                        last_sample_time = current_time
                        frame_index += 1
                        
                        logger.debug(f"采集RTSP帧: {frame_index}, 时间戳: {current_time:.2f}s")
                    else:
                        self.frames_dropped += 1
                    
                    # 防止过度消耗CPU
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"RTSP帧处理异常: {e}")
                    if not await self._reconnect():
                        break
            
        except Exception as e:
            logger.error(f"RTSP帧生产失败: {e}")
        finally:
            await self.cleanup()
    
    async def _reconnect(self) -> bool:
        """重连机制"""
        if self.reconnect_count >= self.max_reconnect_attempts:
            logger.error("RTSP流重连次数超限，放弃重连")
            return False
        
        self.reconnect_count += 1
        logger.info(f"RTSP流重连中 (第{self.reconnect_count}次)...")
        
        await self.cleanup()
        await asyncio.sleep(1)
        
        return await self._connect_stream()
    
    async def cleanup(self):
        """清理RTSP资源"""
        if self.cap:
            self.cap.release()
            self.cap = None
        self.is_active = False
        self.connection_stable = False
        logger.debug(f"RTSP流资源已清理: {self.source_id}")
    
    def get_source_info(self) -> Dict[str, Any]:
        """获取RTSP流信息"""
        uptime = 0
        if self.connection_start_time:
            uptime = (now() - self.connection_start_time).total_seconds()
        
        return {
            'source_id': self.source_id,
            'source_type': self.source_type,
            'rtsp_url': self.rtsp_url,
            'fps': self.fps,
            'is_active': self.is_active,
            'connection_stable': self.connection_stable,
            'frames_captured': self.frames_captured,
            'frames_dropped': self.frames_dropped,
            'reconnect_count': self.reconnect_count,
            'uptime_seconds': uptime,
            'connection_start_time': self.connection_start_time.isoformat() if self.connection_start_time else None
        }


class StreamFactory:
    """流工厂 - 统一创建不同类型的数据源"""
    
    @staticmethod
    def create_stream(source_type: str, source_id: str, source_path: str, **kwargs) -> StreamSource:
        """创建流对象"""
        if source_type == 'video_file':
            return VideoFileStream(source_id, source_path)
        elif source_type == 'rtsp_stream':
            max_reconnect = kwargs.get('max_reconnect_attempts', 5)
            return RealtimeRTSPStream(source_id, source_path, max_reconnect)
        else:
            raise ValueError(f"不支持的流类型: {source_type}")
    
    @staticmethod
    def detect_source_type(source_path: str) -> str:
        """自动检测数据源类型"""
        if source_path.startswith(('rtsp://', 'rtmp://', 'http://')):
            return 'rtsp_stream'
        else:
            return 'video_file'