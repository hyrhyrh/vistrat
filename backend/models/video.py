"""
视频相关数据模型
"""

from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field
from utils.timezone_utils import now, now_isoformat


class VideoConfig(BaseModel):
    """视频配置模型"""
    source: str = Field(..., description="视频源路径")
    type: str = Field(default="local", description="视频类型: local/rtsp")
    analysis_interval: int = Field(default=10, description="分析间隔(秒)")
    buffer_duration: int = Field(default=11, description="缓冲区时长(秒)")


class VideoStatus(BaseModel):
    """视频状态模型"""
    is_running: bool = Field(default=False, description="是否正在运行")
    current_source: str = Field(default="", description="当前视频源")
    fps: float = Field(default=30.0, description="帧率")
    resolution: Dict[str, int] = Field(default={"width": 0, "height": 0}, description="分辨率")
    last_analysis: str = Field(default_factory=lambda: now_isoformat(), description="最后分析时间")


class VideoInfo(BaseModel):
    """视频信息模型"""
    width: int
    height: int
    fps: float
    duration: Optional[float] = None
    total_frames: Optional[int] = None


class VideoFrame(BaseModel):
    """视频帧模型"""
    timestamp: str
    frame_data: bytes
    frame_index: int