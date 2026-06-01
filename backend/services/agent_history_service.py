"""
AI Agent历史记录服务
"""
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, desc, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_async_session
from models.agent_history import AgentHistoryDB, AgentSessionDB
from agent.core.types import Intent, ProcessedData, ReportOutput
from agent.exceptions import AgentHistoryException


class AgentHistoryService:
    """
    AI Agent历史记录服务

    功能:
    - 保存对话历史记录
    - 管理对话会话
    - 查询历史记录
    - 搜索和过滤
    """

    async def save_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        question: str,
        intent: Intent,
        data: ProcessedData,
        report: ReportOutput
    ) -> AgentHistoryDB:
        """
        保存对话历史记录

        Args:
            db: 数据库会话
            user_id: 用户ID
            session_id: 会话ID
            question: 用户问题
            intent: 意图分析结果
            data: 处理后的数据
            report: 报告输出

        Returns:
            AgentHistoryDB: 历史记录对象

        Raises:
            AgentHistoryException: 保存失败
        """
        try:
            # 创建历史记录
            history = AgentHistoryDB(
                user_id=user_id,
                session_id=session_id,
                question=question,
                intent=intent.model_dump(),  # Pydantic V2
                data_summary=data.summary,
                insights=report.metadata.get("insights", ""),
                report_markdown=report.markdown,
                report_html=report.html,
                extra_metadata=report.metadata
            )

            db.add(history)

            # 更新会话信息
            await self._update_session(db, user_id, session_id, question)

            await db.commit()
            await db.refresh(history)

            return history

        except Exception as e:
            await db.rollback()
            raise AgentHistoryException(f"保存历史记录失败: {str(e)}") from e

    async def _update_session(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        question: str
    ):
        """
        更新会话信息

        Args:
            db: 数据库会话
            user_id: 用户ID
            session_id: 会话ID
            question: 问题(用于生成标题)
        """
        # 查询现有会话
        stmt = select(AgentSessionDB).where(AgentSessionDB.id == session_id)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if session:
            # 更新现有会话
            session.message_count += 1
            session.last_message_at = datetime.now()
        else:
            # 创建新会话
            session = AgentSessionDB(
                id=session_id,
                user_id=user_id,
                title=self._generate_session_title(question),
                message_count=1,
                last_message_at=datetime.now()
            )
            db.add(session)

    def _generate_session_title(self, question: str, max_length: int = 30) -> str:
        """
        生成会话标题

        Args:
            question: 用户问题
            max_length: 最大长度

        Returns:
            str: 会话标题
        """
        if len(question) <= max_length:
            return question
        return question[:max_length] + "..."

    async def get_user_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
        session_id: Optional[uuid.UUID] = None
    ) -> List[AgentHistoryDB]:
        """
        获取用户历史记录

        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量
            session_id: 可选的会话ID过滤

        Returns:
            List[AgentHistoryDB]: 历史记录列表
        """
        stmt = select(AgentHistoryDB).where(AgentHistoryDB.user_id == user_id)

        if session_id:
            stmt = stmt.where(AgentHistoryDB.session_id == session_id)

        stmt = stmt.order_by(desc(AgentHistoryDB.created_at)).limit(limit).offset(offset)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_sessions(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentSessionDB]:
        """
        获取用户会话列表

        Args:
            db: 数据库会话
            user_id: 用户ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            List[AgentSessionDB]: 会话列表
        """
        stmt = (
            select(AgentSessionDB)
            .where(AgentSessionDB.user_id == user_id)
            .order_by(desc(AgentSessionDB.last_message_at))
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_history_by_id(
        self,
        db: AsyncSession,
        history_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[AgentHistoryDB]:
        """
        根据ID获取历史记录

        Args:
            db: 数据库会话
            history_id: 历史记录ID
            user_id: 用户ID(权限验证)

        Returns:
            Optional[AgentHistoryDB]: 历史记录对象
        """
        stmt = select(AgentHistoryDB).where(
            AgentHistoryDB.id == history_id,
            AgentHistoryDB.user_id == user_id
        )

        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def search_history(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        keyword: str,
        limit: int = 20
    ) -> List[AgentHistoryDB]:
        """
        搜索历史记录

        Args:
            db: 数据库会话
            user_id: 用户ID
            keyword: 搜索关键词
            limit: 返回数量限制

        Returns:
            List[AgentHistoryDB]: 匹配的历史记录
        """
        stmt = (
            select(AgentHistoryDB)
            .where(
                AgentHistoryDB.user_id == user_id,
                or_(
                    AgentHistoryDB.question.contains(keyword),
                    AgentHistoryDB.insights.contains(keyword)
                )
            )
            .order_by(desc(AgentHistoryDB.created_at))
            .limit(limit)
        )

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_history(
        self,
        db: AsyncSession,
        history_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        删除历史记录

        Args:
            db: 数据库会话
            history_id: 历史记录ID
            user_id: 用户ID(权限验证)

        Returns:
            bool: 是否删除成功
        """
        try:
            history = await self.get_history_by_id(db, history_id, user_id)

            if not history:
                return False

            await db.delete(history)
            await db.commit()

            return True

        except Exception as e:
            await db.rollback()
            raise AgentHistoryException(f"删除历史记录失败: {str(e)}") from e

    async def delete_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> bool:
        """
        删除整个会话(包括所有历史记录)

        Args:
            db: 数据库会话
            session_id: 会话ID
            user_id: 用户ID(权限验证)

        Returns:
            bool: 是否删除成功
        """
        try:
            stmt = select(AgentSessionDB).where(
                AgentSessionDB.id == session_id,
                AgentSessionDB.user_id == user_id
            )

            result = await db.execute(stmt)
            session = result.scalar_one_or_none()

            if not session:
                return False

            # CASCADE DELETE会自动删除关联的历史记录
            await db.delete(session)
            await db.commit()

            return True

        except Exception as e:
            await db.rollback()
            raise AgentHistoryException(f"删除会话失败: {str(e)}") from e

    async def get_statistics(
        self,
        db: AsyncSession,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        获取用户统计信息

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            Dict[str, Any]: 统计信息
        """
        # 总对话数
        total_conversations = await db.scalar(
            select(func.count(AgentHistoryDB.id))
            .where(AgentHistoryDB.user_id == user_id)
        )

        # 总会话数
        total_sessions = await db.scalar(
            select(func.count(AgentSessionDB.id))
            .where(AgentSessionDB.user_id == user_id)
        )

        # 最近对话时间
        last_conversation = await db.scalar(
            select(AgentHistoryDB.created_at)
            .where(AgentHistoryDB.user_id == user_id)
            .order_by(desc(AgentHistoryDB.created_at))
            .limit(1)
        )

        return {
            "total_conversations": total_conversations or 0,
            "total_sessions": total_sessions or 0,
            "last_conversation_at": last_conversation.isoformat() if last_conversation else None
        }


# 全局单例
agent_history_service = AgentHistoryService()
