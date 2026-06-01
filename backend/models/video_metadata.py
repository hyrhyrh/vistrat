"""
视频元数据模型
支持离线视频和实时流的完整元数据管理
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid
from utils.timezone_utils import now


class VideoType(str, Enum):
    """视频类型枚举"""
    LOCAL = "local"           # 本地文件
    RTSP = "rtsp"            # RTSP流
    WEBRTC = "webrtc"        # WebRTC流
    HLS = "hls"              # HLS流
    CAMERA = "camera"        # 摄像头


class VideoStatus(str, Enum):
    """视频状态枚举"""
    PENDING = "pending"       # 待处理
    UPLOADING = "uploading"   # 上传中
    READY = "ready"          # 就绪
    ANALYZING = "analyzing"   # 分析中
    COMPLETED = "completed"   # 已完成
    ERROR = "error"          # 错误
    DELETED = "deleted"      # 已删除


class AnalysisStatus(str, Enum):
    """分析状态枚举"""
    NOT_STARTED = "not_started"   # 未开始
    QUEUED = "queued"            # 排队中
    PROCESSING = "processing"     # 处理中
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"            # 失败
    STOPPED = "stopped"          # 已停止


class VideoMetadata(BaseModel):
    """视频元数据模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="视频唯一ID")
    name: str = Field(..., description="视频名称")
    original_filename: str = Field(..., description="原始文件名")
    type: VideoType = Field(..., description="视频类型")
    status: VideoStatus = Field(default=VideoStatus.PENDING, description="视频状态")
    
    # 技术属性
    file_size: Optional[int] = Field(None, description="文件大小(字节)")
    duration: Optional[float] = Field(None, description="视频时长(秒)")
    fps: Optional[float] = Field(None, description="帧率")
    resolution: Optional[Dict[str, int]] = Field(None, description="分辨率 {width, height}")
    format: Optional[str] = Field(None, description="视频格式")
    codec: Optional[str] = Field(None, description="编码格式")
    
    # 存储属性
    storage_path: Optional[str] = Field(None, description="存储路径")
    minio_bucket: Optional[str] = Field(None, description="MinIO存储桶")
    minio_object_key: Optional[str] = Field(None, description="MinIO对象键")
    thumbnail_path: Optional[str] = Field(None, description="缩略图路径")
    
    # 业务属性
    description: Optional[str] = Field(None, description="视频描述")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    category: Optional[str] = Field(None, description="分类")
    location: Optional[str] = Field(None, description="拍摄地点")
    
    # 时间属性
    created_at: datetime = Field(default_factory=now, description="创建时间")
    updated_at: datetime = Field(default_factory=now, description="更新时间")
    uploaded_at: Optional[datetime] = Field(None, description="上传时间")
    analyzed_at: Optional[datetime] = Field(None, description="分析时间")
    
    # 分析相关
    analysis_config: Optional[Dict[str, Any]] = Field(None, description="分析配置")
    prompt_templates: List[str] = Field(default_factory=list, description="使用的提示词模板ID")
    
    class Config:
        use_enum_values = True


class VideoAnalysisTask(BaseModel):
    """视频分析任务模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="任务ID")
    video_id: str = Field(..., description="视频ID")
    status: AnalysisStatus = Field(default=AnalysisStatus.NOT_STARTED, description="分析状态")
    
    # 分析配置
    prompt_template_ids: List[str] = Field(..., description="使用的提示词模板ID列表")
    analysis_interval: int = Field(default=10, description="分析间隔(秒)")
    confidence_threshold: float = Field(default=0.7, description="置信度阈值")
    enable_annotation: bool = Field(default=True, description="是否启用图像标注")
    
    # 进度跟踪
    progress: float = Field(default=0.0, description="分析进度(0-100)")
    current_frame: int = Field(default=0, description="当前处理帧")
    total_frames: int = Field(default=0, description="总帧数")
    
    # 结果统计
    total_detections: int = Field(default=0, description="总检测数")
    alert_count: int = Field(default=0, description="告警数量")
    processed_duration: float = Field(default=0.0, description="已处理时长")
    
    # 时间属性
    created_at: datetime = Field(default_factory=now, description="创建时间")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    
    # 错误信息
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        use_enum_values = True


class StreamMetadata(BaseModel):
    """实时流元数据模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="流ID")
    name: str = Field(..., description="流名称")
    type: VideoType = Field(..., description="流类型")
    source_url: str = Field(..., description="流源地址")
    
    # 连接配置
    username: Optional[str] = Field(None, description="认证用户名")
    password: Optional[str] = Field(None, description="认证密码")
    transport_protocol: Optional[str] = Field(default="tcp", description="传输协议")
    
    # 流状态
    is_active: bool = Field(default=False, description="是否激活")
    is_connected: bool = Field(default=False, description="是否连接")
    connection_status: str = Field(default="disconnected", description="连接状态")
    
    # 流属性
    fps: Optional[float] = Field(None, description="实际帧率")
    resolution: Optional[Dict[str, int]] = Field(None, description="分辨率")
    bitrate: Optional[int] = Field(None, description="码率")
    
    # 分析配置
    enable_analysis: bool = Field(default=False, description="是否启用分析")
    prompt_template_ids: List[str] = Field(default_factory=list, description="使用的提示词模板ID")
    analysis_interval: int = Field(default=5, description="分析间隔(秒)")
    
    # 统计信息
    total_frames_received: int = Field(default=0, description="总接收帧数")
    total_analysis_count: int = Field(default=0, description="总分析次数")
    last_frame_time: Optional[datetime] = Field(None, description="最后帧时间")
    
    # 时间属性
    created_at: datetime = Field(default_factory=now, description="创建时间")
    updated_at: datetime = Field(default_factory=now, description="更新时间")
    connected_at: Optional[datetime] = Field(None, description="连接时间")
    
    class Config:
        use_enum_values = True