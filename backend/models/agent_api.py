"""
AI Agent API响应模型
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class HistoryResponse(BaseModel):
    """历史记录响应模型"""
    id: str = Field(..., description="历史记录ID")
    session_id: str = Field(..., description="会话ID")
    question: str = Field(..., description="用户问题")
    intent: Dict[str, Any] = Field(..., description="意图分析结果")
    data_summary: Optional[Dict[str, Any]] = Field(None, description="数据摘要")
    insights: Optional[str] = Field(None, description="AI分析结果")
    report_markdown: Optional[str] = Field(None, description="Markdown报告")
    report_html: Optional[str] = Field(None, description="HTML报告")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    """会话响应模型"""
    id: str = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    message_count: int = Field(..., description="消息数量")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""
    total: int = Field(..., description="总数")
    items: List[HistoryResponse] = Field(..., description="历史记录列表")


class SessionListResponse(BaseModel):
    """会话列表响应"""
    total: int = Field(..., description="总数")
    items: List[SessionResponse] = Field(..., description="会话列表")


class StatisticsResponse(BaseModel):
    """统计信息响应"""
    total_conversations: int = Field(..., description="总对话数")
    total_sessions: int = Field(..., description="总会话数")
    last_conversation_at: Optional[str] = Field(None, description="最后对话时间")


class DeleteResponse(BaseModel):
    """删除响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="消息")
