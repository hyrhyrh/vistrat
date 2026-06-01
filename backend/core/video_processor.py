"""
视频处理核心模块
负责视频流读取、帧缓存、分析触发
"""

import asyncio
import cv2
import time
import logging
from datetime import datetime
from collections import deque
# from concurrent.futures import ThreadPoolExecutor  # 🔧 ARM兼容：不再需要
from typing import AsyncGenerator, Dict, Any

from models.video import VideoInfo, VideoFrame
from models.time_range import TimeRange
from config.settings import VideoConfig
from core.analyzer import MultiModalAnalyzer
from utils.timezone_utils import now, now_isoformat


logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频流处理器"""
    
    def __init__(self, video_source: str):
        self.video_source = video_source
        self.cap = cv2.VideoCapture(video_source)
        
        # 验证视频源
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频源: {video_source}")
            
        # 获取视频信息
        ret, frame = self.cap.read()
        if not ret or frame is None:
            self.cap.release()
            raise ValueError(f"无法读取视频帧: {video_source}")
        
        # 初始化视频信息
        self.video_info = VideoInfo(
            width=int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            fps=self.cap.get(cv2.CAP_PROP_FPS) or 30.0,
            total_frames=int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        )
        
        # 重置到开头
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        
        # 初始化组件
        self.buffer = deque(maxlen=int(self.video_info.fps * VideoConfig.BUFFER_DURATION))
        # 🔧 ARM兼容：移除未使用的ThreadPoolExecutor
        self.analyzer = MultiModalAnalyzer()
        self.last_analysis = now().timestamp()
        self._running = False
        self.lock = asyncio.Lock()
        self.frame_queue = asyncio.Queue()
        self.start_push_queue = 0
        
        logger.info(f"视频处理器初始化完成: {video_source}")
        logger.info(f"视频信息: {self.video_info.width}x{self.video_info.height}, {self.video_info.fps}fps")

    @property
    def fps(self) -> float:
        """获取视频帧率"""
        return self.video_info.fps

    async def frame_generator(self) -> AsyncGenerator[Dict[str, Any], None]:
        """异步帧生成器"""
        while self._running:
            start_time = time.monotonic()
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("视频播放结束，准备重连...")
                await self._reconnect()
                continue
                
            # 构建帧数据
            frame_data = {
                "frame": frame,
                "timestamp": now().strftime("%Y-%m-%d-%H-%M-%S"),
                "index": len(self.buffer)
            }
            
            # 添加到缓冲区
            self.buffer.append(frame_data)
            
            # 推送到WebSocket队列
            if self.start_push_queue:
                await self.frame_queue.put(frame)
                
            yield frame_data
            
            # 控制帧生成速度
            elapsed = time.monotonic() - start_time
            await asyncio.sleep(max(0, 1/self.fps - elapsed))

    async def _reconnect(self):
        """视频流重连逻辑"""
        logger.info("重新连接视频流...")
        await asyncio.sleep(VideoConfig.WS_RETRY_INTERVAL)
        self.cap.release()
        self.cap = cv2.VideoCapture(self.video_source)

    async def start_processing(self):
        """启动视频处理流水线"""
        self._running = True
        count = 0
        analysis_tasks = set()
        
        logger.info("开始视频处理流水线")
        
        try:
            async for frame_data in self.frame_generator():
                count += 1
                
                # 定时触发分析
                time_since_analysis = now().timestamp() - self.last_analysis
                frame_threshold = self.fps * VideoConfig.ANALYSIS_INTERVAL
                
                if time_since_analysis >= VideoConfig.ANALYSIS_INTERVAL and count >= frame_threshold:
                    logger.info(f"触发分析 - 帧数: {count}, 间隔: {time_since_analysis:.1f}s")
                    count = 0
                    
                    # 创建带异常处理的分析任务
                    task = asyncio.create_task(self._safe_trigger_analysis())
                    analysis_tasks.add(task)
                    task.add_done_callback(analysis_tasks.discard)
                    
                    self.last_analysis = now().timestamp()
                    
                # 清理已完成的任务
                analysis_tasks = {t for t in analysis_tasks if not t.done()}
                
        except Exception as e:
            logger.error(f"视频处理流水线异常: {str(e)}")
        finally:
            # 等待所有分析任务完成
            if analysis_tasks:
                await asyncio.gather(*analysis_tasks, return_exceptions=True)
            logger.info("视频处理流水线已停止")
    
    async def _safe_trigger_analysis(self):
        """带异常处理的分析触发器"""
        try:
            await self.trigger_analysis()
        except Exception as e:
            logger.error(f"分析任务异常: {str(e)}", exc_info=True)

    async def trigger_analysis(self):
        """触发异步AI分析"""
        try:
            async with self.lock:
                clip = list(self.buffer)
                if not clip:
                    logger.warning("缓冲区为空，跳过分析")
                    return
                
                logger.info(f"开始分析视频片段，帧数: {len(clip)}")
                
                # 提取帧数据和时间戳
                frames = [f["frame"] for f in clip]
                time_range = TimeRange(
                    start_time=clip[0]['timestamp'], 
                    end_time=clip[-1]['timestamp']
                )
                
                # 调用AI分析
                result = await self.analyzer.analyze(frames, self.fps, time_range)
                
                # 处理分析结果
                if result and result.get("alert") != "无异常":
                    from ..core.alert_service import AlertService
                    await AlertService.notify(result)
                    logger.info(f"检测到异常: {result.get('alert')}")
                else:
                    logger.info("视频分析完成，无异常检测")
                    
        except Exception as e:
            logger.error(f"视频分析失败: {str(e)}")

    async def video_streamer(self, websocket):
        """WebSocket视频流推送"""
        try:
            while self._running:
                frame = await self.frame_queue.get()
                
                # 编码帧为JPEG
                ret, buffer = cv2.imencode('.jpg', frame, 
                    [cv2.IMWRITE_JPEG_QUALITY, VideoConfig.JPEG_QUALITY])
                
                if ret:
                    await websocket.send_bytes(buffer.tobytes())
                    
        except Exception as e:
            logger.error(f"视频流推送失败: {str(e)}")

    def stop(self):
        """停止视频处理"""
        self._running = False
        if self.cap:
            self.cap.release()
        logger.info("视频处理器已停止")