"""
视频流实时分析任务数据库模型
支持任务级别管理、时间调度、ROI配置
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from database.connection import Base


class StreamAnalysisTaskDB(Base):
    """视频流实时分析任务数据库表"""
    __tablename__ = 'stream_analysis_tasks'
    __table_args__ = {'comment': '视频流实时分析任务表 - 支持任务级别管理、时间调度、ROI配置'}

    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='任务唯一ID')

    # 关联字段
    stream_id = Column(UUID(as_uuid=True), nullable=False, comment='视频流ID')
    algorithm_config_id = Column(UUID(as_uuid=True), nullable=False, comment='算法配置ID')

    # 基本信息
    task_name = Column(String(255), nullable=False, comment='任务名称')
    status = Column(String(20), nullable=False, default='enabled', comment='任务状态(enabled/disabled/running/error/scheduled)')
    is_active = Column(Boolean, nullable=False, default=True, comment='是否激活')
    auto_recover = Column(Boolean, nullable=False, default=True, comment='是否自动恢复')

    # JSON配置
    time_config = Column(JSONB, nullable=False, default={}, comment='时间配置JSON：支持多时间段、跨天时间、星期选择')
    roi_config = Column(JSONB, default={}, comment='ROI区域配置JSON：支持矩形和多边形感兴趣区域')

    # 执行配置
    priority = Column(Integer, nullable=False, default=1, comment='优先级(1-10)')
    confidence_threshold = Column(Float, nullable=False, default=0.7, comment='置信度阈值(0-1)')
    analysis_interval = Column(Integer, nullable=False, default=10, comment='分析间隔(秒)')

    # 调度时间
    last_run_at = Column(TIMESTAMP(timezone=True), comment='上次运行时间')
    next_run_at = Column(TIMESTAMP(timezone=True), comment='下次运行时间')

    # 运行统计
    run_count = Column(Integer, nullable=False, default=0, comment='运行次数')
    error_count = Column(Integer, nullable=False, default=0, comment='错误次数')
    last_error_message = Column(Text, comment='最后错误信息')
    total_frames_processed = Column(Integer, nullable=False, default=0, comment='总处理帧数')
    total_alerts_generated = Column(Integer, nullable=False, default=0, comment='总告警数')
    avg_processing_time = Column(Float, default=0, comment='平均处理时间(秒)')

    # 时间戳
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        comment='创建时间'
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )

    # 操作人
    created_by = Column(UUID(as_uuid=True), comment='创建人ID')
    updated_by = Column(UUID(as_uuid=True), comment='更新人ID')
