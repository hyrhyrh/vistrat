"""
视频分析结果数据库模型
存储AI分析的详细结果和性能指标
"""

from uuid import uuid4

from sqlalchemy import Column, Text, Integer, Float, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from database.connection import Base


class VideoAnalysisResultDB(Base):
    """视频分析结果数据库表"""
    __tablename__ = 'video_analysis_results'
    __table_args__ = {'comment': '视频分析结果表：存储AI分析的详细结果和性能指标'}

    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='结果唯一ID')

    # 关联字段
    video_file_id = Column(UUID(as_uuid=True), nullable=False, comment='视频文件ID')
    template_id = Column(UUID(as_uuid=True), nullable=False, comment='模板ID')

    # 分析状态
    status = Column(
        ENUM('not_started', 'queued', 'processing', 'completed', 'failed', 'stopped',
             name='analysis_status_enum', create_type=False),
        default='not_started',
        comment='分析状态'
    )

    # 分析结果
    analysis_result = Column(Text, comment='分析结果文本')
    confidence_score = Column(Float, comment='置信度分数(0-1)')
    processing_time = Column(Integer, comment='处理时间(毫秒)')

    # 时间戳
    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        comment='创建时间'
    )
    completed_at = Column(TIMESTAMP(timezone=True), comment='完成时间')
