"""
AI分析调用日志服务
处理AI多模态分析调用日志的增删查改操作
纯异步版本
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import select, desc, func, and_

from models.ai_analysis_log import (
    AIAnalysisLogDB,
    AIAnalysisLogCreate,
    AIAnalysisLogResponse,
    AIAnalysisLogStats,
    AnalysisCallStatus
)
from database.connection import DatabaseManager
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


def format_confidence_score(confidence: Any) -> Optional[str]:
    """格式化置信度分数，保留2位小数并限制长度"""
    if confidence is None:
        return None

    try:
        if isinstance(confidence, str):
            confidence = float(confidence)
        elif not isinstance(confidence, (int, float)):
            return None

        # 保留2位小数并转为字符串
        formatted = f"{confidence:.2f}"

        # 确保长度不超过10个字符
        if len(formatted) > 10:
            formatted = formatted[:10]

        return formatted
    except (ValueError, TypeError):
        logger.warning(f"无法格式化置信度分数: {confidence}")
        return None


class AIAnalysisLogService:
    """AI分析调用日志服务（纯异步版本）"""

    @staticmethod
    async def create_log(log_data: AIAnalysisLogCreate) -> Optional[str]:
        """创建分析调用日志"""
        async with DatabaseManager.get_session() as session:
            try:
                db_log = AIAnalysisLogDB(
                    id=uuid4(),
                    task_id=log_data.task_id,
                    video_id=log_data.video_id,
                    algorithm_id=log_data.algorithm_id,
                    algorithm_config_id=log_data.algorithm_config_id,
                    call_status=log_data.call_status,
                    api_endpoint=log_data.api_endpoint,
                    model_name=log_data.model_name,
                    frame_index=log_data.frame_index,
                    frame_timestamp=log_data.frame_timestamp,
                    request_data=log_data.request_data,
                    response_data=log_data.response_data,
                    response_time_ms=log_data.response_time_ms,
                    confidence_score=log_data.confidence_score,
                    error_message=log_data.error_message,
                    error_code=log_data.error_code
                )

                session.add(db_log)
                await session.flush()
                await session.refresh(db_log)
                await session.commit()

                logger.debug(f"AI分析日志创建成功: {db_log.id}")
                return str(db_log.id)
            except Exception as e:
                await session.rollback()
                logger.error(f"创建AI分析日志失败: {e}")
                return None

    @staticmethod
    async def log_success_call(
        task_id: str,
        video_id: str,
        algorithm_id: str,
        algorithm_config_id: str,
        model_name: str,
        frame_index: int,
        frame_timestamp: str,
        request_data: Dict[str, Any],
        response_data: Dict[str, Any],
        response_time_ms: int,
        confidence_score: str = None
    ) -> Optional[str]:
        """记录成功的AI调用"""
        log_data = AIAnalysisLogCreate(
            task_id=task_id,
            video_id=video_id,
            algorithm_id=algorithm_id,
            algorithm_config_id=algorithm_config_id,
            call_status=AnalysisCallStatus.SUCCESS.value,
            model_name=model_name,
            frame_index=frame_index,
            frame_timestamp=frame_timestamp,
            request_data=request_data,
            response_data=response_data,
            response_time_ms=response_time_ms,
            confidence_score=format_confidence_score(confidence_score)
        )

        return await AIAnalysisLogService.create_log(log_data)

    @staticmethod
    async def log_failed_call(
        task_id: str,
        video_id: str,
        algorithm_id: str,
        algorithm_config_id: str,
        model_name: str,
        frame_index: int,
        frame_timestamp: str,
        request_data: Dict[str, Any],
        error_message: str,
        error_code: str = None,
        response_time_ms: int = None
    ) -> Optional[str]:
        """记录失败的AI调用"""
        log_data = AIAnalysisLogCreate(
            task_id=task_id,
            video_id=video_id,
            algorithm_id=algorithm_id,
            algorithm_config_id=algorithm_config_id,
            call_status=AnalysisCallStatus.FAILED.value,
            model_name=model_name,
            frame_index=frame_index,
            frame_timestamp=frame_timestamp,
            request_data=request_data,
            response_data=None,
            response_time_ms=response_time_ms,
            error_message=error_message,
            error_code=error_code
        )

        return await AIAnalysisLogService.create_log(log_data)

    @staticmethod
    async def get_logs_by_task(task_id: str, limit: int = 100) -> List[AIAnalysisLogResponse]:
        """获取指定任务的所有日志"""
        async with DatabaseManager.get_session() as session:
            try:
                stmt = (
                    select(AIAnalysisLogDB)
                    .where(AIAnalysisLogDB.task_id == task_id)
                    .order_by(desc(AIAnalysisLogDB.created_at))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                logs = result.scalars().all()

                return [
                    AIAnalysisLogResponse(
                        id=str(log.id),
                        task_id=str(log.task_id),
                        video_id=str(log.video_id),
                        algorithm_id=log.algorithm_id,
                        algorithm_config_id=str(log.algorithm_config_id),
                        call_status=log.call_status,
                        api_endpoint=log.api_endpoint,
                        model_name=log.model_name,
                        frame_index=log.frame_index,
                        frame_timestamp=log.frame_timestamp,
                        response_time_ms=log.response_time_ms,
                        confidence_score=log.confidence_score,
                        error_message=log.error_message,
                        error_code=log.error_code,
                        call_date=log.call_date,
                        created_at=log.created_at
                    ) for log in logs
                ]
            except Exception as e:
                logger.error(f"获取任务日志失败: {e}")
                return []

    @staticmethod
    async def get_logs_by_video(video_id: str, limit: int = 100) -> List[AIAnalysisLogResponse]:
        """获取指定视频的所有日志"""
        async with DatabaseManager.get_session() as session:
            try:
                stmt = (
                    select(AIAnalysisLogDB)
                    .where(AIAnalysisLogDB.video_id == video_id)
                    .order_by(desc(AIAnalysisLogDB.created_at))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                logs = result.scalars().all()

                return [
                    AIAnalysisLogResponse(
                        id=str(log.id),
                        task_id=str(log.task_id),
                        video_id=str(log.video_id),
                        algorithm_id=log.algorithm_id,
                        algorithm_config_id=str(log.algorithm_config_id),
                        call_status=log.call_status,
                        api_endpoint=log.api_endpoint,
                        model_name=log.model_name,
                        frame_index=log.frame_index,
                        frame_timestamp=log.frame_timestamp,
                        response_time_ms=log.response_time_ms,
                        confidence_score=log.confidence_score,
                        error_message=log.error_message,
                        error_code=log.error_code,
                        call_date=log.call_date,
                        created_at=log.created_at
                    ) for log in logs
                ]
            except Exception as e:
                logger.error(f"获取视频日志失败: {e}")
                return []

    @staticmethod
    async def get_recent_logs(hours: int = 24, limit: int = 100) -> List[AIAnalysisLogResponse]:
        """获取最近的分析日志"""
        async with DatabaseManager.get_session() as session:
            try:
                cutoff_time = now() - timedelta(hours=hours)

                stmt = (
                    select(AIAnalysisLogDB)
                    .where(AIAnalysisLogDB.call_date >= cutoff_time)
                    .order_by(desc(AIAnalysisLogDB.call_date))
                    .limit(limit)
                )

                result = await session.execute(stmt)
                logs = result.scalars().all()

                return [
                    AIAnalysisLogResponse(
                        id=str(log.id),
                        task_id=str(log.task_id),
                        video_id=str(log.video_id),
                        algorithm_id=log.algorithm_id,
                        algorithm_config_id=str(log.algorithm_config_id),
                        call_status=log.call_status,
                        api_endpoint=log.api_endpoint,
                        model_name=log.model_name,
                        frame_index=log.frame_index,
                        frame_timestamp=log.frame_timestamp,
                        response_time_ms=log.response_time_ms,
                        confidence_score=log.confidence_score,
                        error_message=log.error_message,
                        error_code=log.error_code,
                        call_date=log.call_date,
                        created_at=log.created_at
                    ) for log in logs
                ]
            except Exception as e:
                logger.error(f"获取最近日志失败: {e}")
                return []

    @staticmethod
    async def get_log_statistics(hours: int = 24) -> AIAnalysisLogStats:
        """获取日志统计信息"""
        async with DatabaseManager.get_session() as session:
            try:
                cutoff_time = now() - timedelta(hours=hours)

                # 总调用次数
                total_stmt = select(func.count(AIAnalysisLogDB.id)).where(
                    AIAnalysisLogDB.call_date >= cutoff_time
                )
                total_calls = await session.scalar(total_stmt) or 0

                # 成功调用次数
                success_stmt = select(func.count(AIAnalysisLogDB.id)).where(
                    and_(
                        AIAnalysisLogDB.call_date >= cutoff_time,
                        AIAnalysisLogDB.call_status == AnalysisCallStatus.SUCCESS.value
                    )
                )
                success_calls = await session.scalar(success_stmt) or 0

                # 失败调用次数
                failed_calls = total_calls - success_calls

                # 成功率
                success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

                # 平均响应时间
                avg_time_stmt = select(func.avg(AIAnalysisLogDB.response_time_ms)).where(
                    and_(
                        AIAnalysisLogDB.call_date >= cutoff_time,
                        AIAnalysisLogDB.response_time_ms.isnot(None)
                    )
                )
                avg_response_time = await session.scalar(avg_time_stmt) or 0

                # 错误统计
                error_stmt = select(
                    AIAnalysisLogDB.error_code,
                    func.count(AIAnalysisLogDB.error_code).label('count')
                ).where(
                    and_(
                        AIAnalysisLogDB.call_date >= cutoff_time,
                        AIAnalysisLogDB.call_status == AnalysisCallStatus.FAILED.value,
                        AIAnalysisLogDB.error_code.isnot(None)
                    )
                ).group_by(AIAnalysisLogDB.error_code).order_by(desc('count')).limit(5)

                error_result = await session.execute(error_stmt)
                most_common_errors = [
                    {"error_code": row.error_code, "count": row.count}
                    for row in error_result
                ]

                return AIAnalysisLogStats(
                    total_calls=total_calls,
                    success_calls=success_calls,
                    failed_calls=failed_calls,
                    success_rate=round(success_rate, 2),
                    avg_response_time=round(float(avg_response_time), 2),
                    total_errors=failed_calls,
                    most_common_errors=most_common_errors
                )
            except Exception as e:
                logger.error(f"获取日志统计失败: {e}")
                return AIAnalysisLogStats(
                    total_calls=0,
                    success_calls=0,
                    failed_calls=0,
                    success_rate=0.0,
                    avg_response_time=0.0,
                    total_errors=0,
                    most_common_errors=[]
                )

    @staticmethod
    async def cleanup_old_logs(days: int = 30) -> int:
        """清理旧日志记录"""
        async with DatabaseManager.get_session() as session:
            try:
                cutoff_date = now() - timedelta(days=days)

                # 计算要删除的记录数
                count_stmt = select(func.count(AIAnalysisLogDB.id)).where(
                    AIAnalysisLogDB.call_date < cutoff_date
                )
                delete_count = await session.scalar(count_stmt) or 0

                if delete_count > 0:
                    # 执行删除
                    delete_stmt = AIAnalysisLogDB.__table__.delete().where(
                        AIAnalysisLogDB.call_date < cutoff_date
                    )
                    await session.execute(delete_stmt)
                    await session.commit()

                    logger.info(f"清理了 {delete_count} 条旧日志记录")

                return delete_count
            except Exception as e:
                logger.error(f"清理旧日志失败: {e}")
                return 0


# 全局服务实例
ai_analysis_log_service = AIAnalysisLogService()
