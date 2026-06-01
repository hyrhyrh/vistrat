"""
检测类型模板数据库模型
预定义的AI检测类型和提示词模板，用于复合检测
"""

from uuid import uuid4

from sqlalchemy import Column, String, Text, Integer, Float, Boolean, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database.connection import Base


class DetectionTypeTemplateDB(Base):
    """检测类型模板数据库表"""
    __tablename__ = 'detection_type_templates'
    __table_args__ = {'comment': '检测类型模板表：预定义的AI检测类型和提示词模板，用于复合检测'}

    # 主键
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='模板唯一ID')

    # 基本信息
    type_code = Column(String(50), nullable=False, comment='类型编码(唯一)，如: safety_helmet, smoking')
    display_name = Column(String(100), nullable=False, comment='显示名称，如: 安全帽检测, 吸烟行为检测')
    category = Column(String(50), nullable=False, comment='类别: safety(安全), behavior(行为), environment(环境)')
    prompt_template = Column(Text, nullable=False, comment='提示词模板内容，用于动态组装复合提示词')
    json_field_name = Column(String(50), nullable=False, comment='AI响应JSON中的字段名，用于解析响应')

    # 配置字段
    severity = Column(String(20), nullable=False, default='medium', comment='违规严重程度: low(低), medium(中), high(高)')
    sort_order = Column(Integer, nullable=False, default=0, comment='在复合提示词中的排序顺序，数字越小越靠前')
    enabled = Column(Boolean, nullable=False, default=True, comment='是否启用')

    # 描述信息
    description = Column(Text, comment='检测类型描述')
    example_scenarios = Column(Text, comment='适用场景示例')

    # 统计字段
    usage_count = Column(Integer, default=0, comment='使用次数')
    detection_count = Column(Integer, default=0, comment='检测次数')
    avg_confidence = Column(Float, default=0.0, comment='平均置信度')

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
