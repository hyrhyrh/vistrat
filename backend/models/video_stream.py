"""
视频流数据库模型（v3.0）
保留核心字段，使用共享 Mixin，新增 project_id
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Text, ARRAY
from sqlalchemy.dialects.postgresql import UUID, ENUM
from pydantic import BaseModel, Field, validator

from models.base import Base, TimestampMixin, ProjectMixin


# 枚举类型定义
class StreamStatusEnum(PyEnum):
    """流状态枚举"""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class StreamTypeEnum(PyEnum):
    """视频流类型枚举"""
    RTSP = "RTSP"
    RTMP = "RTMP"
    HLS = "HLS"
    WEBRTC = "WEBRTC"
    HTTP_FLV = "HTTP_FLV"
    LOCAL_CAMERA = "LOCAL_CAMERA"


# SQLAlchemy 数据库模型
class VideoStreamDB(TimestampMixin, ProjectMixin, Base):
    """视频流基础信息表"""
    __tablename__ = "video_streams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    stream_url = Column(String(1000), nullable=False)
    stream_type = Column(
        ENUM(StreamTypeEnum, name='stream_type_enum', create_type=False),
        default=StreamTypeEnum.RTSP,
        nullable=False,
    )
    location = Column(String(255))
    group_name = Column(String(100))
    description = Column(Text)
    tags = Column(ARRAY(Text), default=[])
    status = Column(
        ENUM(StreamStatusEnum, name='stream_status_enum', create_type=False),
        default=StreamStatusEnum.OFFLINE,
        nullable=False,
    )

    @property
    def hls_url(self) -> Optional[str]:
        """HLS 播放地址占位（由 mediamtx 提供）"""
        return None


# Pydantic 模型
class VideoStreamCreate(BaseModel):
    """创建视频流请求"""
    name: str = Field(..., min_length=1, max_length=255, description="摄像头名称")
    stream_url: str = Field(..., description="视频流地址")
    stream_type: StreamTypeEnum = Field(default=StreamTypeEnum.RTSP, description="流类型")
    location: Optional[str] = Field(None, max_length=255, description="位置")
    group_name: Optional[str] = Field(None, max_length=100, description="分组")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    tags: List[str] = Field(default=[], description="标签列表")
    project_id: Optional[str] = Field(None, description="项目ID")

    @validator('stream_url')
    def validate_stream_url(cls, v):
        """验证流地址格式"""
        if not v:
            raise ValueError('流地址不能为空')
        valid_prefixes = ['rtsp://', 'rtmp://', 'http://', 'https://', '/dev/video']
        if not any(v.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError('不支持的流地址格式')
        return v


class VideoStreamUpdate(BaseModel):
    """更新视频流请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="摄像头名称")
    stream_url: Optional[str] = Field(None, description="视频流地址")
    stream_type: Optional[StreamTypeEnum] = Field(None, description="流类型")
    location: Optional[str] = Field(None, max_length=255, description="位置")
    group_name: Optional[str] = Field(None, max_length=100, description="分组")
    description: Optional[str] = Field(None, max_length=1000, description="描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")
    status: Optional[StreamStatusEnum] = Field(None, description="状态")
    project_id: Optional[str] = Field(None, description="项目ID")


class VideoStreamResponse(BaseModel):
    """视频流响应"""
    id: str = Field(..., description="流ID")
    name: str = Field(..., description="摄像头名称")
    stream_url: str = Field(..., description="视频流地址")
    stream_type: StreamTypeEnum = Field(..., description="流类型")
    location: Optional[str] = Field(None, description="位置")
    group_name: Optional[str] = Field(None, description="分组")
    description: Optional[str] = Field(None, description="描述")
    tags: List[str] = Field(..., description="标签列表")
    status: StreamStatusEnum = Field(..., description="状态")
    project_id: Optional[str] = Field(None, description="项目ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    hls_url: Optional[str] = Field(None, description="HLS播放地址")

    class Config:
        from_attributes = True


class VideoStreamAnalysisTemplateCreate(BaseModel):
    """视频流分析模板配置请求"""
    template_ids: List[str] = Field(..., description="模板ID列表")
    priority: Optional[int] = Field(1, ge=1, le=5, description="优先级")
    confidence_threshold: Optional[float] = Field(0.7, ge=0.1, le=1.0, description="置信度阈值")
