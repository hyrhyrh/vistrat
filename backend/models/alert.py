"""
告警数据库模型（v3.0）
分区表设计，按月分区，JSONB 存储分析结果
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import Column, String, Text, PrimaryKeyConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM
from pydantic import BaseModel, Field

from models.base import Base, TimestampMixin, ProjectMixin


class AlertStatusEnum(PyEnum):
    """告警状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class AlertDB(TimestampMixin, ProjectMixin, Base):
    """告警表（按月分区）"""
    __tablename__ = "alerts"
    __table_args__ = (
        PrimaryKeyConstraint('id', 'created_at'),
        {'postgresql_partition_by': 'RANGE (created_at)'},
    )

    id = Column(UUID(as_uuid=True), default=uuid4, nullable=False)
    stream_id = Column(UUID(as_uuid=True), nullable=False)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    level = Column(String(20), nullable=False, default='warning')
    status = Column(
        ENUM(AlertStatusEnum, name='alert_status', create_type=False, values_callable=lambda e: [m.value for m in e]),
        default=AlertStatusEnum.PENDING,
        nullable=False,
    )
    result = Column(JSONB)
    snapshot_path = Column(String(500))
    message = Column(Text)

    # 视频片段字段（Week 3B 新增）
    # clip_url: 片段可访问 URL；clip_status: pending/ready/failed/skipped
    clip_url = Column(String(512), nullable=True)
    clip_status = Column(String(16), nullable=False, default="pending")


# Pydantic 模型
class AlertCreate(BaseModel):
    """创建告警请求"""
    stream_id: str = Field(..., description="视频流ID")
    task_id: Optional[str] = Field(None, description="分析任务ID")
    level: str = Field(default="warning", description="告警级别")
    result: Optional[Dict[str, Any]] = Field(None, description="分析结果 JSONB")
    snapshot_path: Optional[str] = Field(None, description="截图路径")
    message: Optional[str] = Field(None, description="告警消息")
    project_id: Optional[str] = Field(None, description="项目ID")


class AlertResponse(BaseModel):
    """告警响应"""
    id: str = Field(..., description="告警ID")
    stream_id: str = Field(..., description="视频流ID")
    task_id: Optional[str] = Field(None, description="分析任务ID")
    level: str = Field(..., description="告警级别")
    status: str = Field(..., description="告警状态")
    result: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    snapshot_path: Optional[str] = Field(None, description="截图路径")
    message: Optional[str] = Field(None, description="告警消息")
    project_id: Optional[str] = Field(None, description="项目ID")
    clip_url: Optional[str] = Field(None, description="视频片段 URL（异步生成，成功后可用）")
    clip_status: str = Field(default="pending", description="片段生成状态：pending/ready/failed/skipped")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    """更新告警请求（仅状态）"""
    status: AlertStatusEnum = Field(..., description="告警状态")


class AlertMessage(BaseModel):
    """WebSocket 告警推送消息（兼容 v2 AlertService）"""
    timestamp: Optional[str] = None
    alert: str = ""
    description: str = ""
    video_file_name: Optional[str] = None
    picture_file_name: Optional[str] = None
    severity: str = "info"
