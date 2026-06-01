"""
任务统计和监控辅助模块

从 stream_task_manager.py 中提取的统计和监控相关功能：
- 单个任务统计信息获取
- 所有任务统计汇总
- 管理器整体统计
- 任务心跳更新
- 错误记录

这些方法原属于 StreamTaskManager 类，提取为独立函数以降低主类复杂度。
"""

import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def get_task_stats(task_id: str, task_stats: Dict, tasks: Dict) -> Optional[Dict[str, Any]]:
    """
    获取任务统计信息

    Args:
        task_id: 任务ID
        task_stats: 任务统计字典 {task_id -> TaskStats}
        tasks: 任务字典 {task_id -> task_data}

    Returns:
        统计信息字典，如果任务不存在返回None
    """
    if task_id not in task_stats:
        return None

    stats = task_stats[task_id]
    uptime_seconds = 0
    if stats.start_time:
        uptime_seconds = int(time.time() - stats.start_time)

    return {
        'task_id': task_id,
        'frames_processed': stats.frames_processed,
        'alerts_generated': stats.alerts_generated,
        'error_count': stats.error_count,
        'uptime_seconds': uptime_seconds,
        'avg_processing_time_ms': round(stats.avg_processing_time_ms, 2),
        'last_error': stats.last_error,
        'last_heartbeat_age_seconds': int(time.time() - stats.last_heartbeat) if stats.last_heartbeat else None
    }


def get_all_tasks_stats(task_stats: Dict, tasks: Dict) -> List[Dict[str, Any]]:
    """
    获取所有任务的统计信息

    Args:
        task_stats: 任务统计字典
        tasks: 任务字典

    Returns:
        统计信息列表
    """
    result = []
    for task_id in task_stats.keys():
        stats = get_task_stats(task_id, task_stats, tasks)
        if stats and task_id in tasks:
            stats['task_name'] = tasks[task_id].get('task_name', 'Unknown')
            stats['status'] = tasks[task_id].get('status', 'unknown')
            result.append(stats)
    return result


def get_manager_stats(
    tasks: Dict,
    task_stats: Dict,
    total_tasks_created: int,
    total_tasks_started: int,
    total_tasks_stopped: int,
    total_tasks_failed: int,
    initialized: bool
) -> Dict[str, Any]:
    """
    获取任务管理器整体统计

    Args:
        tasks: 任务字典
        task_stats: 任务统计字典
        total_tasks_created: 总创建任务数
        total_tasks_started: 总启动任务数
        total_tasks_stopped: 总停止任务数
        total_tasks_failed: 总失败任务数
        initialized: 是否已初始化

    Returns:
        管理器统计信息
    """
    active_count = sum(1 for task in tasks.values() if task.get('is_active', False))
    running_count = sum(1 for task in tasks.values() if task.get('is_running', False))

    total_errors = sum(stats.error_count for stats in task_stats.values())
    total_frames = sum(stats.frames_processed for stats in task_stats.values())
    total_alerts = sum(stats.alerts_generated for stats in task_stats.values())

    return {
        'total_tasks': len(tasks),
        'active_tasks': active_count,
        'running_tasks': running_count,
        'total_tasks_created': total_tasks_created,
        'total_tasks_started': total_tasks_started,
        'total_tasks_stopped': total_tasks_stopped,
        'total_tasks_failed': total_tasks_failed,
        'total_frames_processed': total_frames,
        'total_alerts_generated': total_alerts,
        'total_errors': total_errors,
        'initialized': initialized
    }


def update_task_heartbeat(
    task_stats: Dict,
    task_id: str,
    frames_processed: int = None,
    alerts_generated: int = None,
    processing_time_ms: float = None
):
    """
    更新任务心跳和统计

    Args:
        task_stats: 任务统计字典
        task_id: 任务ID
        frames_processed: 处理的帧数(增量)
        alerts_generated: 生成的告警数(增量)
        processing_time_ms: 处理时间(毫秒)
    """
    if task_id not in task_stats:
        return

    stats = task_stats[task_id]
    stats.last_heartbeat = time.time()

    if frames_processed is not None:
        stats.frames_processed += frames_processed

    if alerts_generated is not None:
        stats.alerts_generated += alerts_generated

    if processing_time_ms is not None:
        # 使用移动平均计算平均处理时间
        if stats.avg_processing_time_ms == 0:
            stats.avg_processing_time_ms = processing_time_ms
        else:
            alpha = 0.3  # 平滑因子
            stats.avg_processing_time_ms = (
                alpha * processing_time_ms +
                (1 - alpha) * stats.avg_processing_time_ms
            )


def record_task_error(task_stats: Dict, task_id: str, error_message: str):
    """
    记录任务错误

    Args:
        task_stats: 任务统计字典
        task_id: 任务ID
        error_message: 错误信息
    """
    if task_id not in task_stats:
        return

    stats = task_stats[task_id]
    stats.error_count += 1
    stats.last_error = error_message[:200]  # 限制长度
