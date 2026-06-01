"""
任务恢复辅助模块

从 stream_task_manager.py 中提取的任务恢复相关功能：
- 异步任务自动恢复
- 同步任务恢复检查（ARM架构兼容）

这些方法原属于 StreamTaskManager 类，提取为独立函数以降低主类复杂度。
主类通过委托调用这些函数。
"""

import asyncio
import logging
from typing import List, Dict, Any

from database.db_utils import get_async_connection, fetch

logger = logging.getLogger(__name__)


async def recover_tasks_async(enable_task_func) -> bool:
    """
    系统重启时自动恢复所有已启用的任务（异步版本）

    Args:
        enable_task_func: 启用任务的异步函数，签名为 async (task_id: str) -> bool

    Returns:
        是否恢复成功
    """
    try:
        logger.info("执行任务自动恢复...")

        conn = await get_async_connection(use_dict_row=True)
        try:
            query = """
                SELECT t.id, t.stream_id, t.task_name, vs.name as stream_name
                FROM stream_analysis_tasks t
                LEFT JOIN video_streams vs ON t.stream_id = vs.id
                WHERE t.status = 'enabled' AND t.is_active = true
                ORDER BY t.priority DESC, t.created_at
            """
            results = await fetch(conn, query)

            if not results:
                logger.info("没有需要恢复的任务")
                return True

            logger.info(f"找到 {len(results)} 个需要恢复的任务")

            async def recover_single_task(row):
                """恢复单个任务的协程"""
                task_id = str(row['id'])
                task_name = row['task_name']
                stream_name = row['stream_name'] or '未知流'

                try:
                    logger.info(f"正在恢复任务: {task_name} (ID: {task_id[:8]}..., 流: {stream_name})")
                    success = await enable_task_func(task_id)

                    if success:
                        logger.info(f"任务恢复成功: {task_name}")
                        return True
                    else:
                        logger.warning(f"任务恢复失败: {task_name}")
                        return False

                except Exception as e:
                    logger.error(f"恢复任务时发生异常: {task_name}, 错误: {e}")
                    return False

            # 并发执行所有任务恢复
            recovery_results = await asyncio.gather(
                *[recover_single_task(row) for row in results],
                return_exceptions=False
            )

            recovered_count = sum(1 for r in recovery_results if r is True)
            failed_count = len(results) - recovered_count

            logger.info(f"任务自动恢复完成 - 成功: {recovered_count}, 失败: {failed_count}, 总计: {len(results)}")
            return True

        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"任务自动恢复失败: {e}", exc_info=True)
        return False


def recover_tasks_sync() -> bool:
    """
    系统重启时自动恢复任务检查（同步版本，ARM架构使用）

    仅记录需要恢复的任务数量，实际恢复将在应用完全启动后异步执行。

    Returns:
        是否检查成功
    """
    try:
        logger.info("执行任务自动恢复检查（ARM同步模式）...")

        from database.db_utils import get_sync_connection

        conn = get_sync_connection(autocommit=True, use_dict_row=False)
        try:
            query = """
                SELECT COUNT(*)
                FROM stream_analysis_tasks t
                WHERE t.status = 'enabled' AND t.is_active = true
            """
            cursor = conn.execute(query)
            count = cursor.fetchone()[0]

            if count == 0:
                logger.info("没有需要恢复的任务")
                return True

            logger.info(f"找到 {count} 个需要恢复的任务（将在应用启动后异步恢复）")
            return True

        finally:
            conn.close()

    except Exception as e:
        logger.error(f"任务自动恢复检查失败: {e}")
        return False
