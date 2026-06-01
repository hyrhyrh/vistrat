"""
视频文件数据库模型
基于SQLAlchemy ORM的PostgreSQL模型定义
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any
from uuid import uuid4

from sqlalchemy import Column, String, Integer, Float, Boolean, Text, TIMESTAMP, ARRAY, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from database.connection import Base


# 枚举类型定义
class VideoStatusEnum(PyEnum):
    """视频状态枚举"""
    PENDING = "PENDING"
    UPLOADING = "UPLOADING" 
    READY = "READY"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    DELETED = "DELETED"


class AnalysisStatusEnum(PyEnum):
    """分析状态枚举"""
    NOT_STARTED = "not_started"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


# SQLAlchemy数据库模型
class VideoFileDB(Base):
    """视频文件数据库表模型"""
    __tablename__ = "video_files"
    __table_args__ = {'comment': '视频文件信息表 - 存储上传的离线视频基本信息和分析状态'}
    
    # 主键和基本信息
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='视频唯一ID')
    name = Column(String(255), nullable=False, comment='视频名称')
    original_filename = Column(String(500), nullable=False, comment='原始文件名')
    file_path = Column(String(1000), nullable=False, comment='文件存储路径(MinIO路径)')
    thumbnail_path = Column(String(1000), comment='缩略图路径')
    
    # 视频基本信息
    file_size = Column(Integer, comment='文件大小(字节)')
    duration = Column(Float, comment='视频时长(秒)')
    fps = Column(Float, comment='帧率')
    width = Column(Integer, comment='视频宽度')
    height = Column(Integer, comment='视频高度')
    format = Column(String(50), comment='视频格式(mp4/avi/mov等)')
    
    # 业务字段
    status = Column(
        ENUM(VideoStatusEnum, name='video_status_enum'), 
        default='PENDING', 
        nullable=False, 
        comment='视频状态'
    )
    tags = Column(ARRAY(Text), default=[], comment='视频标签数组')
    description = Column(Text, comment='视频描述')
    analysis_progress = Column(Integer, default=0, comment='分析进度百分比')
    
    # 时间戳
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.current_timestamp(), 
        comment='创建时间'
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )
    analyzed_at = Column(TIMESTAMP(timezone=True), comment='分析完成时间')
    
    # 分析结果统计
    total_alerts = Column(Integer, default=0, comment='总告警数量')
    last_alert_at = Column(TIMESTAMP(timezone=True), comment='最后告警时间')




# Pydantic模型用于API
class VideoFileCreate(BaseModel):
    """创建视频文件请求模型"""
    name: str = Field(..., description="视频名称")
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件存储路径")
    thumbnail_path: Optional[str] = Field(None, description="缩略图路径")
    description: Optional[str] = Field(None, description="视频描述")
    tags: List[str] = Field(default=[], description="视频标签")
    
    # 视频技术信息
    file_size: Optional[int] = Field(None, description="文件大小")
    duration: Optional[float] = Field(None, description="视频时长")
    fps: Optional[float] = Field(None, description="帧率")
    width: Optional[int] = Field(None, description="视频宽度")
    height: Optional[int] = Field(None, description="视频高度")
    format: Optional[str] = Field(None, description="视频格式")
    
    # 业务状态
    status: Optional[VideoStatusEnum] = Field(VideoStatusEnum.PENDING, description="视频状态")


class VideoFileUpdate(BaseModel):
    """更新视频文件请求模型"""
    name: Optional[str] = Field(None, description="视频名称")
    description: Optional[str] = Field(None, description="视频描述")
    tags: Optional[List[str]] = Field(None, description="视频标签")
    status: Optional[VideoStatusEnum] = Field(None, description="视频状态")
    analysis_progress: Optional[int] = Field(None, ge=0, le=100, description="分析进度")


class VideoFileResponse(BaseModel):
    """视频文件响应模型"""
    id: str = Field(..., description="视频ID")
    name: str = Field(..., description="视频名称")
    original_filename: str = Field(..., description="原始文件名")
    file_path: str = Field(..., description="文件路径")
    thumbnail_path: Optional[str] = Field(None, description="缩略图路径")
    
    # 视频信息
    file_size: Optional[int] = Field(None, description="文件大小")
    duration: Optional[float] = Field(None, description="视频时长")
    fps: Optional[float] = Field(None, description="帧率")
    width: Optional[int] = Field(None, description="视频宽度")  
    height: Optional[int] = Field(None, description="视频高度")
    format: Optional[str] = Field(None, description="视频格式")
    
    # 业务字段
    status: VideoStatusEnum = Field(..., description="视频状态")
    tags: List[str] = Field(..., description="视频标签")
    description: Optional[str] = Field(None, description="视频描述")
    analysis_progress: int = Field(..., description="分析进度")
    
    # 时间戳
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    analyzed_at: Optional[datetime] = Field(None, description="分析完成时间")
    
    # 统计信息
    total_alerts: int = Field(..., description="总告警数量")
    last_alert_at: Optional[datetime] = Field(None, description="最后告警时间")

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
        
    @classmethod
    def from_orm(cls, obj):
        """自定义ORM转换方法，处理UUID序列化"""
        return cls(
            id=str(obj.id) if hasattr(obj.id, '__str__') else obj.id,
            name=obj.name,
            original_filename=obj.original_filename,
            file_path=obj.file_path,
            thumbnail_path=obj.thumbnail_path,
            file_size=obj.file_size,
            duration=obj.duration,
            fps=obj.fps,
            width=obj.width,
            height=obj.height,
            format=obj.format,
            status=obj.status.value if hasattr(obj.status, 'value') else str(obj.status),
            tags=obj.tags or [],
            description=obj.description,
            analysis_progress=obj.analysis_progress,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
            analyzed_at=obj.analyzed_at,
            total_alerts=obj.total_alerts,
            last_alert_at=obj.last_alert_at
        )


class VideoAnalysisTemplateCreate(BaseModel):
    """创建视频分析模板关联请求（支持复合检测）"""
    video_id: str = Field(..., description="视频ID")
    template_ids: List[str] = Field(..., description="AI模型配置ID列表")
    detection_type_codes: Optional[List[str]] = Field(default=[], description="检测类型编码列表（复合检测）")
    priority: Optional[int] = Field(1, ge=1, le=5, description="优先级")


class VideoAnalysisTemplateResponse(BaseModel):
    """视频分析模板关联响应"""
    id: str = Field(..., description="关联ID")
    video_id: str = Field(..., description="视频ID")
    template_id: str = Field(..., description="模板ID")
    template_name: str = Field(..., description="模板名称")
    analysis_status: AnalysisStatusEnum = Field(..., description="分析状态")
    progress: int = Field(..., description="进度百分比")
    
    class Config:
        from_attributes = True