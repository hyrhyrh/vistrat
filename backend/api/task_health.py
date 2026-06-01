"""
任务健康监控API端点

提供查询任务健康监控状态、统计信息、任务恢复记录等功能
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Any

router = APIRouter(prefix="/api/task-health", tags=["任务健康监控"])


@router.get("/statistics", summary="获取健康监控统计信息")
async def get_health_statistics() -> Dict[str, Any]:
    """
    获取任务健康监控的统计信息

    包括：
    - 运行状态
    - 总检查次数
    - 总恢复次数
    - 总失败次数
    - 任务和流的监控统计
    - 配置信息
    """
    try:
        from services.task_health_monitor import task_health_monitor

        if not task_health_monitor.is_running:
            return {
                "status": "stopped",
                "message": "任务健康监控服务未运行"
            }

        stats = task_health_monitor.get_statistics()
        return {
            "status": "success",
            "data": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/task-records", summary="获取任务恢复记录")
async def get_task_records() -> Dict[str, Any]:
    """
    获取所有任务的恢复记录

    包括每个任务的：
    - 任务信息
    - 最后检查时间
    - 失败次数
    - 恢复尝试次数
    - 连续失败次数
    - 最后错误信息
    """
    try:
        from services.task_health_monitor import task_health_monitor

        if not task_health_monitor.is_running:
            return {
                "status": "stopped",
                "message": "任务健康监控服务未运行",
                "data": []
            }

        records = task_health_monitor.get_task_records()
        return {
            "status": "success",
            "count": len(records),
            "data": records
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取任务记录失败: {str(e)}")


@router.get("/stream-records", summary="获取视频流健康记录")
async def get_stream_records() -> Dict[str, Any]:
    """
    获取所有视频流的健康记录

    包括每个流的：
    - 流信息
    - 当前状态（在线/离线）
    - 最后检查时间
    - 最后在线/离线时间
    - 检查次数
    - 连续失败次数
    - 最后错误信息
    """
    try:
        from services.task_health_monitor import task_health_monitor

        if not task_health_monitor.is_running:
            return {
                "status": "stopped",
                "message": "任务健康监控服务未运行",
                "data": []
            }

        records = task_health_monitor.get_stream_records()
        return {
            "status": "success",
            "count": len(records),
            "data": records
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取流记录失败: {str(e)}")


@router.get("/status", summary="获取健康监控服务状态")
async def get_health_status() -> Dict[str, Any]:
    """
    获取健康监控服务的运行状态

    快速检查服务是否正在运行
    """
    try:
        from services.task_health_monitor import task_health_monitor

        return {
            "status": "success",
            "is_running": task_health_monitor.is_running,
            "started_at": task_health_monitor.started_at.isoformat() if task_health_monitor.started_at else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取服务状态失败: {str(e)}")


@router.post("/manual-check", summary="手动触发健康检查")
async def trigger_manual_check() -> Dict[str, Any]:
    """
    手动触发一次健康检查

    立即检查所有启用的任务状态，不等待定时器
    """
    try:
        from services.task_health_monitor import task_health_monitor

        if not task_health_monitor.is_running:
            raise HTTPException(
                status_code=400,
                detail="任务健康监控服务未运行，无法执行手动检查"
            )

        # 触发手动检查
        await task_health_monitor._check_all_tasks()

        return {
            "status": "success",
            "message": "手动健康检查已完成",
            "timestamp": task_health_monitor.task_records[list(task_health_monitor.task_records.keys())[0]].last_check_time.isoformat()
            if task_health_monitor.task_records else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"执行手动检查失败: {str(e)}")


@router.get("/summary", summary="获取监控概览")
async def get_health_summary() -> Dict[str, Any]:
    """
    获取健康监控的概览信息

    汇总所有关键信息，适合仪表板显示
    """
    try:
        from services.task_health_monitor import task_health_monitor

        if not task_health_monitor.is_running:
            return {
                "status": "stopped",
                "message": "任务健康监控服务未运行"
            }

        # 获取统计信息
        stats = task_health_monitor.get_statistics()

        # 获取问题任务（有连续失败的）
        task_records = task_health_monitor.get_task_records()
        problem_tasks = [
            r for r in task_records
            if r['consecutive_failures'] > 0
        ]

        # 获取离线流
        stream_records = task_health_monitor.get_stream_records()
        offline_streams = [
            r for r in stream_records
            if r['status'] == 'OFFLINE'
        ]

        return {
            "status": "success",
            "data": {
                "is_running": stats['is_running'],
                "uptime_hours": stats['uptime_hours'],
                "total_checks": stats['total_checks'],
                "total_recoveries": stats['total_recoveries'],
                "total_failures": stats['total_failures'],
                "tasks_monitored": stats['task_statistics']['total_tasks_monitored'],
                "tasks_with_issues": len(problem_tasks),
                "problem_tasks": problem_tasks[:5],  # 只返回前5个
                "streams_monitored": stats['stream_statistics']['total_streams_monitored'],
                "online_streams": stats['stream_statistics']['online_streams'],
                "offline_streams": stats['stream_statistics']['offline_streams'],
                "offline_stream_details": offline_streams[:5],  # 只返回前5个
                "health_score": _calculate_health_score(stats, len(problem_tasks), len(offline_streams))
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取概览信息失败: {str(e)}")


def _calculate_health_score(
    stats: Dict[str, Any],
    problem_tasks_count: int,
    offline_streams_count: int
) -> int:
    """
    计算系统健康分数（0-100）

    考虑因素：
    - 问题任务占比
    - 离线流占比
    - 失败率
    """
    score = 100

    # 问题任务扣分（最多扣30分）
    total_tasks = stats['task_statistics']['total_tasks_monitored']
    if total_tasks > 0:
        problem_ratio = problem_tasks_count / total_tasks
        score -= int(problem_ratio * 30)

    # 离线流扣分（最多扣30分）
    total_streams = stats['stream_statistics']['total_streams_monitored']
    if total_streams > 0:
        offline_ratio = offline_streams_count / total_streams
        score -= int(offline_ratio * 30)

    # 失败率扣分（最多扣40分）
    total_recoveries = stats.get('total_recoveries', 0)
    total_failures = stats.get('total_failures', 0)
    if total_recoveries + total_failures > 0:
        failure_ratio = total_failures / (total_recoveries + total_failures)
        score -= int(failure_ratio * 40)

    return max(0, min(100, score))
