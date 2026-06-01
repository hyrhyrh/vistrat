"""
AI分析调用日志模型
记录每次AI多模态分析调用的详细信息
"""

from sqlalchemy import Column, String, Text, DateTime, Boolean, UUID, Integer, JSON
from uuid import uuid4
import enum
from database.connection import Base
from utils.timezone_utils import now


class AnalysisCallStatus(enum.Enum):
    """分析调用状态枚举"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AIAnalysisLogDB(Base):
    """AI分析调用日志数据库表"""
    __tablename__ = 'ai_analysis_logs'
    __table_args__ = {
        'comment': 'AI多模态分析调用日志表 - 记录每次AI分析调用的详细信息',
        'extend_existing': True
    }
    
    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='日志唯一ID')
    
    # 关联信息
    task_id = Column(UUID(as_uuid=True), comment='分析任务ID')
    video_id = Column(UUID(as_uuid=True), comment='视频文件ID')
    algorithm_id = Column(String(255), comment='编排算法ID')
    algorithm_config_id = Column(UUID(as_uuid=True), comment='编排算法配置ID')
    
    # 调用信息
    call_status = Column(String(20), default=AnalysisCallStatus.SUCCESS.value, comment='调用状态')
    api_endpoint = Column(String(500), comment='API端点URL')
    model_name = Column(String(100), comment='使用的AI模型名称')
    
    # 帧信息
    frame_index = Column(Integer, comment='帧索引')
    frame_timestamp = Column(String(20), comment='帧时间戳')
    
    # 请求和响应数据
    request_data = Column(JSON, comment='请求数据JSON')
    response_data = Column(JSON, comment='响应数据JSON')
    
    # 性能指标
    response_time_ms = Column(Integer, comment='响应时间（毫秒）')
    confidence_score = Column(String(10), comment='置信度分数')
    
    # 错误信息
    error_message = Column(Text, comment='错误信息（如果失败）')
    error_code = Column(String(50), comment='错误代码')
    
    # 时间戳
    call_date = Column(DateTime, default=now, comment='调用日期')
    created_at = Column(DateTime, default=now, comment='创建时间')
    updated_at = Column(DateTime, default=now, onupdate=now, comment='更新时间')


# Pydantic模型用于API
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any


class AIAnalysisLogCreate(BaseModel):
    """创建AI分析日志请求模型"""
    model_config = ConfigDict(protected_namespaces=())
    
    task_id: str
    video_id: str
    algorithm_id: str
    algorithm_config_id: str
    call_status: str = AnalysisCallStatus.SUCCESS.value
    api_endpoint: Optional[str] = None
    model_name: Optional[str] = None
    frame_index: Optional[int] = None
    frame_timestamp: Optional[str] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    response_time_ms: Optional[int] = None
    confidence_score: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class AIAnalysisLogResponse(BaseModel):
    """AI分析日志响应模型"""
    model_config = ConfigDict(protected_namespaces=(), from_attributes=True)
    
    id: str
    task_id: str
    video_id: str
    algorithm_id: str
    algorithm_config_id: str
    call_status: str
    api_endpoint: Optional[str]
    model_name: Optional[str]
    frame_index: Optional[int]
    frame_timestamp: Optional[str]
    response_time_ms: Optional[int]
    confidence_score: Optional[str]
    error_message: Optional[str]
    error_code: Optional[str]
    call_date: datetime
    created_at: datetime
    


class AIAnalysisLogStats(BaseModel):
    """AI分析日志统计模型"""
    total_calls: int
    success_calls: int
    failed_calls: int
    success_rate: float
    avg_response_time: float
    total_errors: int
    most_common_errors: list