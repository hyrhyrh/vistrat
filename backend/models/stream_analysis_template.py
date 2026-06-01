"""
流分析模板数据库模型
视频流AI分析配置模板
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from database.connection import Base


class StreamAnalysisTemplateDB(Base):
    """流分析模板数据库表"""
    __tablename__ = 'stream_analysis_templates'
    __table_args__ = {'comment': '流分析模板表：视频流AI分析配置模板'}

    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='模板唯一ID')

    # 关联字段
    stream_id = Column(UUID(as_uuid=True), nullable=False, comment='视频流ID')
    template_id = Column(String(100), nullable=False, comment='模板ID')
    template_name = Column(String(255), nullable=False, comment='模板名称')

    # 配置字段
    priority = Column(Integer, default=1, comment='优先级')
    enabled = Column(Boolean, comment='是否启用')
    confidence_threshold = Column(Float, default=0.7, comment='置信度阈值')

    # 分析状态
    analysis_status = Column(
        ENUM('NOT_STARTED', 'RUNNING', 'COMPLETED', 'FAILED', 'STOPPED',
             name='stream_analysis_status_enum', create_type=False),
        default='NOT_STARTED',
        comment='分析状态'
    )

    # 统计字段
    alerts_count = Column(Integer, default=0, comment='告警数量')
    detection_count = Column(Integer, default=0, comment='检测数量')
    confidence_avg = Column(Float, comment='平均置信度')

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
    last_detection_at = Column(TIMESTAMP(timezone=True), comment='最后检测时间')

    # 错误信息
    error_message = Column(Text, comment='错误信息')
