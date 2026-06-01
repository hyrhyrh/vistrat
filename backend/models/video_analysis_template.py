"""
视频分析模板数据模型
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import Column, String, Text, Boolean, Integer, Float, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database.connection import Base


class VideoAnalysisTemplateDB(Base):
    """视频分析模板数据库表"""
    __tablename__ = 'video_analysis_templates'
    __table_args__ = {'comment': '视频分析模板表 - 存储每个视频配置的AI分析算法', 'extend_existing': True}
    
    # 主键和关联
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='模板唯一ID')
    video_id = Column(UUID(as_uuid=True), comment='关联的视频ID')
    template_id = Column(UUID(as_uuid=True), comment='模板引用ID')
    template_name = Column(String(255), nullable=False, comment='模板名称')
    
    # 模板基本信息
    name = Column(String(255), nullable=False, comment='算法名称')
    category = Column(String(100), nullable=False, comment='算法分类')
    description = Column(Text, comment='算法描述')
    prompt_content = Column(Text, nullable=False, comment='分析提示词')

    # 复合检测关联字段（新增）
    detection_type_code = Column(String(50), comment='检测类型编码（关联detection_type_templates表）')

    # 执行配置
    priority = Column(Integer, default=0, comment='执行优先级')
    enabled = Column(Boolean, default=True, comment='是否启用')
    is_enabled = Column(Boolean, default=True, comment='向下兼容字段')
    
    # 执行状态
    analysis_status = Column(String(50), default='not_started', comment='分析状态')
    progress = Column(Integer, default=0, comment='执行进度')
    alerts_count = Column(Integer, default=0, comment='告警数量')
    confidence_avg = Column(Float, default=0.0, comment='平均置信度')
    analysis_duration = Column(Integer, comment='分析耗时(秒)')
    error_message = Column(Text, comment='错误信息')
    
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
    started_at = Column(TIMESTAMP(timezone=True), comment='开始执行时间')
    completed_at = Column(TIMESTAMP(timezone=True), comment='完成时间')