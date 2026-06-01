"""
视频流算法配置数据模型
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, UUID as SQLAlchemyUUID, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from database.connection import Base


class VideoStreamAlgorithmConfigDB(Base):
    """视频流算法配置数据库模型"""
    __tablename__ = "video_stream_algorithm_configs"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    stream_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("video_streams.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(String(255), nullable=False)
    template_name = Column(String(255))
    priority = Column(Integer, default=1)
    confidence_threshold = Column(Float, default=0.7)
    is_active = Column(Boolean, default=True)

    # 复合检测配置（新增）
    detection_type_codes = Column(
        JSON,
        default=[],
        comment='用户选择的检测类型编码列表，JSONB数组格式，示例: ["smoking", "using_phone"]'
    )

    created_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    updated_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    created_by = Column(String(255))

    # 唯一约束：一个流的同一个算法模板只能配置一次
    __table_args__ = (
        UniqueConstraint('stream_id', 'template_id', name='uk_stream_algorithm_config'),
    )


class VideoStreamAlgorithmConfigHistoryDB(Base):
    """视频流算法配置历史数据库模型（审计表）"""
    __tablename__ = "video_stream_algorithm_config_history"
    
    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, server_default="gen_random_uuid()")
    config_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    stream_id = Column(PostgreSQLUUID(as_uuid=True), nullable=False)
    template_id = Column(String(255), nullable=False)
    template_name = Column(String(255))
    priority = Column(Integer)
    confidence_threshold = Column(Float)
    is_active = Column(Boolean)
    operation = Column(String(20), nullable=False)  # 'INSERT', 'UPDATE', 'DELETE'
    operation_at = Column(DateTime, server_default="CURRENT_TIMESTAMP")
    operated_by = Column(String(255))


# Pydantic模型用于API输入输出

class VideoStreamAlgorithmConfigCreate(BaseModel):
    """创建视频流算法配置请求模型"""
    template_ids: List[str] = Field(..., description="算法模板ID列表")
    priority: int = Field(1, ge=1, le=10, description="优先级，1-10")
    confidence_threshold: float = Field(0.7, ge=0.0, le=1.0, description="置信度阈值，0.0-1.0")
    detection_type_codes: List[str] = Field(default=[], description="用户选择的检测类型编码列表")


class VideoStreamAlgorithmConfigUpdate(BaseModel):
    """更新视频流算法配置请求模型"""
    template_ids: Optional[List[str]] = Field(None, description="算法模板ID列表")
    priority: Optional[int] = Field(None, ge=1, le=10, description="优先级，1-10")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度阈值，0.0-1.0")
    detection_type_codes: Optional[List[str]] = Field(None, description="用户选择的检测类型编码列表")
    is_active: Optional[bool] = Field(None, description="是否启用")


class VideoStreamAlgorithmConfigResponse(BaseModel):
    """视频流算法配置响应模型"""
    id: str = Field(..., description="配置ID")
    stream_id: str = Field(..., description="视频流ID")
    template_id: str = Field(..., description="算法模板ID")
    template_name: Optional[str] = Field(None, description="算法模板名称")
    priority: int = Field(..., description="优先级")
    confidence_threshold: float = Field(..., description="置信度阈值")
    detection_type_codes: List[str] = Field(default=[], description="用户选择的检测类型编码列表")
    is_active: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")


class VideoStreamAlgorithmConfigListResponse(BaseModel):
    """视频流算法配置列表响应模型"""
    success: bool = Field(True, description="是否成功")
    total: int = Field(..., description="总数")
    templates: List[VideoStreamAlgorithmConfigResponse] = Field(..., description="配置列表")
    stream_id: str = Field(..., description="视频流ID")
    message: Optional[str] = Field(None, description="消息")


class VideoStreamAlgorithmConfigHistoryResponse(BaseModel):
    """视频流算法配置历史响应模型"""
    id: str = Field(..., description="历史记录ID")
    config_id: str = Field(..., description="配置ID")
    stream_id: str = Field(..., description="视频流ID")
    template_id: str = Field(..., description="算法模板ID")
    template_name: Optional[str] = Field(None, description="算法模板名称")
    priority: Optional[int] = Field(None, description="优先级")
    confidence_threshold: Optional[float] = Field(None, description="置信度阈值")
    is_active: Optional[bool] = Field(None, description="是否启用")
    operation: str = Field(..., description="操作类型")
    operation_at: datetime = Field(..., description="操作时间")
    operated_by: Optional[str] = Field(None, description="操作者")


# 兼容性模型（保持与前端的兼容性）
class LegacyTemplateResponse(BaseModel):
    """兼容旧版API的模板响应格式"""
    template_id: str = Field(..., description="算法模板ID")
    priority: int = Field(..., description="优先级")
    confidence_threshold: float = Field(..., description="置信度阈值")
    configured_at: str = Field(..., description="配置时间ISO格式")


class LegacyConfigResponse(BaseModel):
    """兼容旧版API的配置响应格式"""
    success: bool = Field(True, description="是否成功")
    templates: List[LegacyTemplateResponse] = Field(..., description="模板列表")
    stream_id: str = Field(..., description="视频流ID")
    total: int = Field(..., description="总数")
    message: Optional[str] = Field(None, description="消息")