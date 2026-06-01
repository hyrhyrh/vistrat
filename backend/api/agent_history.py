"""
AI Agent历史记录API端点
"""
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_async_session as get_db
from api.auth import get_current_user
from services.agent_history_service import agent_history_service
from models.auth import UserDB
from models.agent_api import (
    HistoryResponse,
    SessionResponse,
    HistoryListResponse,
    SessionListResponse,
    StatisticsResponse,
    DeleteResponse
)

router = APIRouter(prefix="/agent/history", tags=["AI Agent History"])


@router.get("/sessions", response_model=SessionListResponse)
async def get_sessions(
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: Optional[str] = Query(None, description="用户ID(可选)"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户会话列表 - 无需认证

    返回用户的所有对话会话,按最后消息时间倒序排列
    """
    # 如果没有提供user_id，返回空列表
    if not user_id:
        return SessionListResponse(total=0, items=[])

    try:
        sessions = await agent_history_service.get_user_sessions(
            db=db,
            user_id=uuid.UUID(user_id),
            limit=limit,
            offset=offset
        )
    except ValueError:
        # user_id格式无效
        return SessionListResponse(total=0, items=[])

    return SessionListResponse(
        total=len(sessions),
        items=[
            SessionResponse(
                id=str(session.id),
                title=session.title,
                message_count=session.message_count,
                last_message_at=session.last_message_at,
                created_at=session.created_at
            )
            for session in sessions
        ]
    )


@router.get("/conversations", response_model=HistoryListResponse)
async def get_conversations(
    session_id: Optional[str] = Query(None, description="会话ID过滤"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    user_id: Optional[str] = Query(None, description="用户ID(可选)"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户对话历史 - 无需认证

    可选择按会话ID过滤,返回对话记录列表
    """
    # 如果没有提供user_id，返回空列表
    if not user_id:
        return HistoryListResponse(total=0, items=[])

    try:
        session_uuid = uuid.UUID(session_id) if session_id else None
        histories = await agent_history_service.get_user_history(
            db=db,
            user_id=uuid.UUID(user_id),
            limit=limit,
            offset=offset,
            session_id=session_uuid
        )
    except ValueError:
        # ID格式无效
        return HistoryListResponse(total=0, items=[])

    return HistoryListResponse(
        total=len(histories),
        items=[
            HistoryResponse(
                id=str(history.id),
                session_id=str(history.session_id),
                question=history.question,
                intent=history.intent,
                data_summary=history.data_summary,
                insights=history.insights,
                report_markdown=history.report_markdown,
                report_html=history.report_html,
                extra_metadata=history.extra_metadata,
                created_at=history.created_at
            )
            for history in histories
        ]
    )


@router.get("/conversations/{history_id}", response_model=HistoryResponse)
async def get_conversation_detail(
    history_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取对话详情

    返回完整的对话记录,包括HTML报告
    """
    try:
        history_uuid = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的历史记录ID")

    history = await agent_history_service.get_history_by_id(
        db=db,
        history_id=history_uuid,
        user_id=current_user.id
    )

    if not history:
        raise HTTPException(status_code=404, detail="历史记录不存在")

    return HistoryResponse(
        id=str(history.id),
        session_id=str(history.session_id),
        question=history.question,
        intent=history.intent,
        data_summary=history.data_summary,
        insights=history.insights,
        report_markdown=history.report_markdown,
        report_html=history.report_html,
        metadata=history.metadata,
        created_at=history.created_at
    )


@router.get("/search", response_model=HistoryListResponse)
async def search_conversations(
    keyword: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    搜索对话历史

    根据关键词搜索问题和分析结果
    """
    histories = await agent_history_service.search_history(
        db=db,
        user_id=current_user.id,
        keyword=keyword,
        limit=limit
    )

    return HistoryListResponse(
        total=len(histories),
        items=[
            HistoryResponse(
                id=str(history.id),
                session_id=str(history.session_id),
                question=history.question,
                intent=history.intent,
                data_summary=history.data_summary,
                insights=history.insights,
                report_markdown=history.report_markdown,
                report_html=history.report_html,
                extra_metadata=history.extra_metadata,
                created_at=history.created_at
            )
            for history in histories
        ]
    )


@router.delete("/conversations/{history_id}", response_model=DeleteResponse)
async def delete_conversation(
    history_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除对话记录

    删除单条对话历史
    """
    try:
        history_uuid = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的历史记录ID")

    success = await agent_history_service.delete_history(
        db=db,
        history_id=history_uuid,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(status_code=404, detail="历史记录不存在")

    return DeleteResponse(
        success=True,
        message="删除成功"
    )


@router.delete("/sessions/{session_id}", response_model=DeleteResponse)
async def delete_session(
    session_id: str,
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除整个会话

    删除会话及其所有对话记录
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的会话ID")

    success = await agent_history_service.delete_session(
        db=db,
        session_id=session_uuid,
        user_id=current_user.id
    )

    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")

    return DeleteResponse(
        success=True,
        message="删除成功"
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    current_user: UserDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取统计信息

    返回用户的对话统计数据
    """
    stats = await agent_history_service.get_statistics(
        db=db,
        user_id=current_user.id
    )

    return StatisticsResponse(**stats)
