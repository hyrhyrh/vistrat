"""
ROI (Region of Interest) 配置数据模型
用于存储视频流分析的感兴趣区域配置
"""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, TIMESTAMP, JSON, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from database.connection import Base


class ROIConfigDB(Base):
    """ROI配置数据库表"""
    __tablename__ = 'roi_configs'
    __table_args__ = {'comment': 'ROI感兴趣区域配置表 - 存储视频流分析的区域设置'}
    
    # 主键和关联
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='ROI配置唯一ID')
    stream_id = Column(UUID(as_uuid=True), nullable=False, comment='关联的视频流ID')
    algorithm_id = Column(String(255), nullable=False, comment='关联的算法ID')
    
    # ROI配置信息
    name = Column(String(255), nullable=False, comment='ROI配置名称')
    description = Column(Text, comment='ROI配置描述')
    
    # ROI区域数据 - 存储为JSON格式
    regions = Column(JSON, nullable=False, comment='ROI区域列表，JSON格式: [{"x": 0, "y": 0, "width": 100, "height": 100}]')
    
    # 配置状态
    enabled = Column(Boolean, default=True, comment='是否启用ROI配置')
    
    # 元数据
    video_width = Column(Integer, comment='视频原始宽度')
    video_height = Column(Integer, comment='视频原始高度')
    
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


# Pydantic数据模型
class ROIRegion(BaseModel):
    """单个ROI区域模型"""
    x: int = Field(..., ge=0, description="区域左上角X坐标")
    y: int = Field(..., ge=0, description="区域左上角Y坐标") 
    width: int = Field(..., gt=0, description="区域宽度")
    height: int = Field(..., gt=0, description="区域高度")
    
    @validator('x', 'y', 'width', 'height')
    def validate_positive_values(cls, v):
        """验证坐标和尺寸为正值"""
        if v < 0:
            raise ValueError('坐标和尺寸必须为非负数')
        return v


class ROIConfigCreate(BaseModel):
    """创建ROI配置请求模型"""
    stream_id: str = Field(..., description="视频流ID")
    algorithm_id: str = Field(..., description="算法ID")
    name: str = Field(..., min_length=1, max_length=255, description="ROI配置名称")
    description: Optional[str] = Field(None, max_length=1000, description="ROI配置描述")
    regions: List[ROIRegion] = Field(..., min_items=1, description="ROI区域列表")
    video_width: Optional[int] = Field(None, gt=0, description="视频原始宽度")
    video_height: Optional[int] = Field(None, gt=0, description="视频原始高度")
    enabled: bool = Field(True, description="是否启用")
    
    @validator('regions')
    def validate_regions(cls, v):
        """验证ROI区域不能为空"""
        if not v:
            raise ValueError('至少需要配置一个ROI区域')
        return v


class ROIConfigUpdate(BaseModel):
    """更新ROI配置请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="ROI配置名称")
    description: Optional[str] = Field(None, max_length=1000, description="ROI配置描述")
    regions: Optional[List[ROIRegion]] = Field(None, description="ROI区域列表")
    video_width: Optional[int] = Field(None, gt=0, description="视频原始宽度")
    video_height: Optional[int] = Field(None, gt=0, description="视频原始高度")
    enabled: Optional[bool] = Field(None, description="是否启用")


class ROIConfigResponse(BaseModel):
    """ROI配置响应模型"""
    id: str = Field(..., description="ROI配置ID")
    stream_id: str = Field(..., description="视频流ID")
    algorithm_id: str = Field(..., description="算法ID")
    name: str = Field(..., description="ROI配置名称")
    description: Optional[str] = Field(None, description="ROI配置描述")
    regions: List[ROIRegion] = Field(..., description="ROI区域列表")
    video_width: Optional[int] = Field(None, description="视频原始宽度")
    video_height: Optional[int] = Field(None, description="视频原始高度")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ROIConfigBatch(BaseModel):
    """批量ROI配置模型"""
    stream_id: str = Field(..., description="视频流ID")
    configs: List[ROIConfigCreate] = Field(..., min_items=1, description="ROI配置列表")
    
    @validator('configs')
    def validate_configs(cls, v):
        """验证配置列表不能为空"""
        if not v:
            raise ValueError('至少需要一个ROI配置')
        return v