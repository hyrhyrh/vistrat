"""
AI Agent历史记录数据模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from database.connection import Base


class AgentHistoryDB(Base):
    """
    AI Agent对话历史表

    保存所有AI分析对话记录
    """
    __tablename__ = "ai_agent_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    question = Column(Text, nullable=False)
    intent = Column(JSONB, nullable=False)
    data_summary = Column(JSONB)
    insights = Column(Text)
    report_markdown = Column(Text)
    report_html = Column(Text)
    extra_metadata = Column(JSONB)  # 使用extra_metadata避免与SQLAlchemy的metadata冲突
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.now, index=True)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.now, onupdate=datetime.now)

    # 关系
    user = relationship("UserDB", back_populates="agent_history")

    def __repr__(self):
        return f"<AgentHistoryDB(id={self.id}, user_id={self.user_id}, question={self.question[:30]}...)>"


class AgentSessionDB(Base):
    """
    AI Agent对话会话表

    管理用户的对话会话
    """
    __tablename__ = "ai_agent_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text)
    message_count = Column(Integer, nullable=False, default=0)
    last_message_at = Column(TIMESTAMP(timezone=True), index=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.now, index=True)

    # 关系
    user = relationship("UserDB", back_populates="agent_sessions")

    def __repr__(self):
        return f"<AgentSessionDB(id={self.id}, user_id={self.user_id}, title={self.title})>"
