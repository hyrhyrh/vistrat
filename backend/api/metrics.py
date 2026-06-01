"""
性能指标API端点
提供系统和服务性能监控接口
"""

from fastapi import APIRouter, Query
from typing import Dict, Any

from services.metrics_collector import metrics_collector

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/latest")
async def get_latest_metrics() -> Dict[str, Any]:
    """
    获取最新性能指标

    Returns:
        包含系统和服务指标的字典
    """
    return metrics_collector.get_latest_metrics()


@router.get("/history")
async def get_metrics_history(
    duration: int = Query(
        default=600,
        ge=60,
        le=3600,
        description="时间范围(秒),最小60秒,最大3600秒(1小时)"
    )
) -> Dict[str, Any]:
    """
    获取历史性能指标

    Args:
        duration: 时间范围(秒),默认600秒(10分钟)

    Returns:
        历史指标数据
    """
    return metrics_collector.get_metrics_history(duration)


@router.get("/summary")
async def get_performance_summary() -> Dict[str, Any]:
    """
    获取性能摘要

    Returns:
        包含平均值、峰值和当前值的性能摘要
    """
    return metrics_collector.get_performance_summary()


@router.get("/health")
async def get_metrics_health() -> Dict[str, Any]:
    """
    获取指标收集器健康状态

    Returns:
        健康状态信息
    """
    latest = metrics_collector.get_latest_metrics()

    if latest.get('status') == 'no_data':
        return {
            'status': 'initializing',
            'message': '指标收集器正在初始化...'
        }

    # 检查数据是否新鲜(最近30秒内)
    import time
    last_timestamp = latest.get('timestamp', 0)
    age_seconds = time.time() - last_timestamp

    if age_seconds > 30:
        return {
            'status': 'stale',
            'message': f'指标数据过期 ({age_seconds:.0f}秒未更新)',
            'last_update': last_timestamp
        }

    return {
        'status': 'healthy',
        'message': '指标收集器运行正常',
        'data_age_seconds': round(age_seconds, 2),
        'metrics_count': {
            'system': len(metrics_collector.system_metrics_history),
            'service': len(metrics_collector.service_metrics_history)
        }
    }
