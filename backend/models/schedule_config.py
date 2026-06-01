"""
时间调度配置数据模型
用于存储视频流分析的时间调度设置，支持每日时间段和星期几配置
"""

from datetime import datetime, time
from typing import List, Optional
from uuid import uuid4
from sqlalchemy import Column, String, Time, Boolean, TIMESTAMP, JSON, Text, ARRAY, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, validator

from database.connection import Base


class ScheduleConfigDB(Base):
    """时间调度配置数据库表"""
    __tablename__ = 'schedule_configs'
    __table_args__ = {'comment': '时间调度配置表 - 存储视频流分析的时间调度设置'}
    
    # 主键和关联
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='调度配置唯一ID')
    stream_id = Column(UUID(as_uuid=True), nullable=False, comment='关联的视频流ID')
    algorithm_id = Column(String(255), nullable=False, comment='关联的算法ID')
    
    # 调度配置信息
    name = Column(String(255), nullable=False, comment='调度配置名称')
    description = Column(Text, comment='调度配置描述')
    
    # 时间配置
    start_time = Column(Time, nullable=False, comment='开始时间 (如: 07:00)')
    end_time = Column(Time, nullable=False, comment='结束时间 (如: 18:00)')
    
    # 星期几配置 - 使用数组存储，1=周一, 2=周二, ..., 7=周日, 0=周日(兼容)
    weekdays = Column(ARRAY(Integer), nullable=False, comment='运行星期几，数组格式: [1,2,3,4,5] 表示周一到周五')
    
    # 高级调度配置 - 存储为JSON格式，支持多个时间段
    time_ranges = Column(JSON, comment='多时间段配置，JSON格式: [{"start_time": "07:00", "end_time": "12:00"}, {"start_time": "14:00", "end_time": "18:00"}]')
    
    # 配置状态
    enabled = Column(Boolean, default=True, comment='是否启用时间调度')
    
    # 时区配置
    timezone = Column(String(50), default='Asia/Shanghai', comment='时区设置')
    
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
class TimeRangeModel(BaseModel):
    """单个时间段模型"""
    start_time: str = Field(..., description="开始时间，格式: HH:MM")
    end_time: str = Field(..., description="结束时间，格式: HH:MM")
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """验证时间格式"""
        try:
            time.fromisoformat(v)
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM 格式，如: 07:30')
        return v
    
    @validator('end_time')
    def validate_time_range(cls, v, values):
        """验证结束时间大于开始时间"""
        if 'start_time' in values:
            start = time.fromisoformat(values['start_time'])
            end = time.fromisoformat(v)
            # 允许跨天的时间范围，如22:00-06:00
            if start >= end:
                # 如果结束时间小于开始时间，认为是跨天的
                pass
        return v


class ScheduleConfigCreate(BaseModel):
    """创建时间调度配置请求模型"""
    stream_id: str = Field(..., description="视频流ID")
    algorithm_id: str = Field(..., description="算法ID")
    name: str = Field(..., min_length=1, max_length=255, description="调度配置名称")
    description: Optional[str] = Field(None, max_length=1000, description="调度配置描述")
    start_time: str = Field(..., description="开始时间，格式: HH:MM")
    end_time: str = Field(..., description="结束时间，格式: HH:MM")
    weekdays: List[int] = Field(..., description="运行星期几，1=周一, 2=周二, ..., 7=周日, 0=周日(兼容)")
    time_ranges: Optional[List[TimeRangeModel]] = Field(None, description="多时间段配置(可选)")
    timezone: str = Field('Asia/Shanghai', description="时区设置")
    enabled: bool = Field(True, description="是否启用")
    
    @validator('weekdays')
    def validate_weekdays(cls, v):
        """验证星期几配置"""
        if not v:
            raise ValueError('至少需要选择一个星期几')
        
        valid_days = {0, 1, 2, 3, 4, 5, 6, 7}  # 0和7都表示周日
        for day in v:
            if day not in valid_days:
                raise ValueError('星期几必须在0-7范围内，0和7表示周日，1-6表示周一到周六')
        
        return v
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        """验证时间格式"""
        try:
            time.fromisoformat(v)
        except ValueError:
            raise ValueError('时间格式错误，应为 HH:MM 格式，如: 07:30')
        return v


class ScheduleConfigUpdate(BaseModel):
    """更新时间调度配置请求模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="调度配置名称")
    description: Optional[str] = Field(None, max_length=1000, description="调度配置描述")
    start_time: Optional[str] = Field(None, description="开始时间，格式: HH:MM")
    end_time: Optional[str] = Field(None, description="结束时间，格式: HH:MM")
    weekdays: Optional[List[int]] = Field(None, description="运行星期几")
    time_ranges: Optional[List[TimeRangeModel]] = Field(None, description="多时间段配置")
    timezone: Optional[str] = Field(None, description="时区设置")
    enabled: Optional[bool] = Field(None, description="是否启用")


class ScheduleConfigResponse(BaseModel):
    """时间调度配置响应模型"""
    id: str = Field(..., description="调度配置ID")
    stream_id: str = Field(..., description="视频流ID")
    algorithm_id: str = Field(..., description="算法ID")
    name: str = Field(..., description="调度配置名称")
    description: Optional[str] = Field(None, description="调度配置描述")
    start_time: str = Field(..., description="开始时间")
    end_time: str = Field(..., description="结束时间")
    weekdays: List[int] = Field(..., description="运行星期几")
    time_ranges: Optional[List[TimeRangeModel]] = Field(None, description="多时间段配置")
    timezone: str = Field(..., description="时区设置")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ScheduleConfigBatch(BaseModel):
    """批量时间调度配置模型"""
    stream_id: str = Field(..., description="视频流ID")
    configs: List[ScheduleConfigCreate] = Field(..., min_items=1, description="调度配置列表")
    
    @validator('configs')
    def validate_configs(cls, v):
        """验证配置列表不能为空"""
        if not v:
            raise ValueError('至少需要一个调度配置')
        return v


class ScheduleCheckRequest(BaseModel):
    """调度检查请求模型"""
    stream_id: str = Field(..., description="视频流ID")
    algorithm_id: str = Field(..., description="算法ID")
    check_time: Optional[datetime] = Field(None, description="检查时间，默认为当前时间")
    

class ScheduleCheckResponse(BaseModel):
    """调度检查响应模型"""
    should_run: bool = Field(..., description="是否应该运行")
    reason: str = Field(..., description="判断原因")
    current_time: datetime = Field(..., description="当前检查时间")
    next_run_time: Optional[datetime] = Field(None, description="下次运行时间")
    config_enabled: bool = Field(..., description="配置是否启用")
    in_time_range: bool = Field(..., description="是否在时间范围内")
    in_weekday_range: bool = Field(..., description="是否在工作日范围内")