"""
分析任务数据库模型（v3.0）
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pydantic import BaseModel, Field

from models.base import Base, TimestampMixin, ProjectMixin


class TaskStatusEnum(PyEnum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisTaskDB(TimestampMixin, ProjectMixin, Base):
    """分析任务表"""
    __tablename__ = "analysis_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    stream_id = Column(
        UUID(as_uuid=True),
        ForeignKey("video_streams.id", ondelete="CASCADE"),
        nullable=False,
    )
    status = Column(
        ENUM(TaskStatusEnum, name='task_status', create_type=False, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatusEnum.PENDING,
        nullable=False,
    )
    prompt = Column(Text)
    config = Column(JSONB)
    result = Column(JSONB)
    started_at = Column(TIMESTAMP(timezone=True))
    stopped_at = Column(TIMESTAMP(timezone=True))
    error_message = Column(Text)


# Pydantic 模型
class AnalysisTaskCreate(BaseModel):
    """创建分析任务请求"""
    stream_id: str = Field(..., description="视频流ID")
    prompt: str = Field(default="请分析画面中是否存在安全违规行为", description="分析提示词")
    config: Optional[Dict[str, Any]] = Field(None, description="任务配置")
    project_id: Optional[str] = Field(None, description="项目ID")


class AnalysisTaskResponse(BaseModel):
    """分析任务响应"""
    id: str = Field(..., description="任务ID")
    stream_id: str = Field(..., description="视频流ID")
    status: str = Field(..., description="任务状态")
    prompt: Optional[str] = Field(None, description="分析提示词")
    config: Optional[Dict[str, Any]] = Field(None, description="任务配置")
    result: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    stopped_at: Optional[datetime] = Field(None, description="停止时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    project_id: Optional[str] = Field(None, description="项目ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True
