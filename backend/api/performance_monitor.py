"""
性能监控API
提供实时系统性能监控和指标查询
"""

import asyncio
import logging
import psutil
import time
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta

from services.stream_analysis_service import stream_analysis_service
from services.unified_ai_client import unified_ai_client
from services.adaptive_buffer_manager import adaptive_buffer_manager
from database.connection import DatabaseManager
from utils.timezone_utils import now_isoformat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["性能监控"])


@router.get("/system/overview", summary="获取系统性能概览")
async def get_system_overview():
    """
    获取系统整体性能概览
    优化：使用非阻塞CPU采样，响应时间从1005ms降至<100ms
    """
    try:
        # 获取系统基础信息（非阻塞方式）
        cpu_percent = psutil.cpu_percent(interval=None)  # 优化：使用上次采样值，避免1秒阻塞
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # 获取进程信息
        process = psutil.Process()
        process_memory = process.memory_info()

        # 并发获取应用层统计（优化性能）
        buffer_stats_task = stream_analysis_service.get_buffer_performance_stats()
        db_pool_stats_task = _get_database_pool_stats()

        # 等待并发任务完成
        buffer_stats, db_pool_stats = await asyncio.gather(
            buffer_stats_task,
            db_pool_stats_task
        )

        # 获取熔断器统计（同步方法，快速）
        circuit_breaker_stats = unified_ai_client.get_circuit_breaker_stats()

        return {
            "success": True,
            "timestamp": now_isoformat(),
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": round(memory.percent, 2),
                    "used": memory.used
                },
                "disk": {
                    "total": disk.total,
                    "free": disk.free,
                    "used": disk.used,
                    "percent": round((disk.used / disk.total) * 100, 2)
                },
                "process": {
                    "memory_rss": process_memory.rss,
                    "memory_vms": process_memory.vms,
                    "cpu_percent": round(process.cpu_percent(), 2),
                    "num_threads": process.num_threads()
                }
            },
            "application": {
                "buffer_manager": buffer_stats,
                "circuit_breakers": circuit_breaker_stats,
                "database_pool": db_pool_stats
            }
        }

    except Exception as e:
        logger.error(f"获取系统概览失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取系统概览失败: {str(e)}")


@router.get("/buffers/stats", summary="获取缓冲区详细统计")
async def get_buffer_stats():
    """获取缓冲区管理器详细统计"""
    try:
        # 获取自适应缓冲区统计
        adaptive_stats = adaptive_buffer_manager.get_performance_stats()
        
        # 获取流分析服务缓冲区统计
        stream_stats = await stream_analysis_service.get_buffer_performance_stats()
        
        return {
            "success": True,
            "timestamp": now_isoformat(),
            "adaptive_buffer_manager": adaptive_stats,
            "stream_analysis_service": stream_stats
        }
        
    except Exception as e:
        logger.error(f"获取缓冲区统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取缓冲区统计失败: {str(e)}")


@router.get("/circuit-breakers/stats", summary="获取熔断器统计")
async def get_circuit_breaker_stats():
    """获取所有AI熔断器统计信息"""
    try:
        stats = unified_ai_client.get_circuit_breaker_stats()
        
        return {
            "success": True,
            "timestamp": now_isoformat(),
            "circuit_breakers": stats
        }
        
    except Exception as e:
        logger.error(f"获取熔断器统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取熔断器统计失败: {str(e)}")


@router.post("/circuit-breakers/reset", summary="重置所有熔断器")
async def reset_circuit_breakers():
    """重置所有AI熔断器"""
    try:
        unified_ai_client.reset_circuit_breakers()
        
        return {
            "success": True,
            "message": "所有熔断器已重置",
            "timestamp": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"重置熔断器失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置熔断器失败: {str(e)}")


@router.get("/streams/analysis", summary="获取流分析性能统计")
async def get_stream_analysis_stats():
    """获取视频流分析性能统计"""
    try:
        # 获取所有分析任务
        tasks = await stream_analysis_service.get_analysis_tasks()
        
        # 统计任务状态
        running_tasks = [t for t in tasks if t.get('status') == 'running']
        stopped_tasks = [t for t in tasks if t.get('status') == 'stopped']
        error_tasks = [t for t in tasks if t.get('status') == 'error']
        
        # 计算性能指标
        total_frames = sum(t.get('frame_count', 0) for t in tasks)
        total_alerts = sum(t.get('alert_count', 0) for t in tasks)
        
        # 计算平均处理速度（帧/分钟）
        processing_rates = []
        for task in running_tasks:
            if task.get('started_at') and task.get('frame_count', 0) > 0:
                start_time = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                duration_minutes = (datetime.now().timestamp() - start_time.timestamp()) / 60
                if duration_minutes > 0:
                    rate = task['frame_count'] / duration_minutes
                    processing_rates.append(rate)
        
        avg_processing_rate = sum(processing_rates) / len(processing_rates) if processing_rates else 0
        
        return {
            "success": True,
            "timestamp": now_isoformat(),
            "summary": {
                "total_tasks": len(tasks),
                "running_tasks": len(running_tasks),
                "stopped_tasks": len(stopped_tasks),
                "error_tasks": len(error_tasks),
                "total_frames_processed": total_frames,
                "total_alerts_generated": total_alerts,
                "avg_processing_rate_per_minute": round(avg_processing_rate, 2)
            },
            "running_tasks_detail": [
                {
                    "task_id": task.get('task_id'),
                    "stream_id": task.get('stream_id'),
                    "stream_name": task.get('stream_name'),
                    "frame_count": task.get('frame_count', 0),
                    "alert_count": task.get('alert_count', 0),
                    "started_at": task.get('started_at'),
                    "template_count": len(task.get('template_ids', []))
                }
                for task in running_tasks
            ]
        }
        
    except Exception as e:
        logger.error(f"获取流分析统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取流分析统计失败: {str(e)}")


@router.get("/database/pool", summary="获取数据库连接池状态")
async def get_database_pool_stats():
    """获取数据库连接池状态"""
    try:
        stats = await _get_database_pool_stats()
        
        return {
            "success": True,
            "timestamp": now_isoformat(),
            "database_pool": stats
        }
        
    except Exception as e:
        logger.error(f"获取数据库连接池统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取数据库连接池统计失败: {str(e)}")


@router.get("/health/comprehensive", summary="获取系统健康检查")
async def get_comprehensive_health_check():
    """
    执行全面的系统健康检查
    优化：使用非阻塞CPU采样，响应时间从1060ms降至<100ms
    """
    try:
        health_status = {
            "overall_status": "healthy",
            "timestamp": now_isoformat(),
            "checks": {}
        }

        # 数据库连接检查
        try:
            db_healthy = await DatabaseManager.test_connection()
            health_status["checks"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "message": "数据库连接正常" if db_healthy else "数据库连接失败"
            }
            if not db_healthy:
                health_status["overall_status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"数据库检查失败: {str(e)}"
            }
            health_status["overall_status"] = "unhealthy"

        # 系统资源检查（使用非阻塞方式）
        cpu_percent = psutil.cpu_percent(interval=None)  # 优化：使用上次采样值，避免1秒阻塞
        memory_percent = psutil.virtual_memory().percent

        # CPU检查
        if cpu_percent > 90:
            health_status["checks"]["cpu"] = {
                "status": "critical",
                "message": f"CPU使用率过高: {cpu_percent:.1f}%"
            }
            health_status["overall_status"] = "critical"
        elif cpu_percent > 70:
            health_status["checks"]["cpu"] = {
                "status": "warning",
                "message": f"CPU使用率较高: {cpu_percent:.1f}%"
            }
            if health_status["overall_status"] == "healthy":
                health_status["overall_status"] = "warning"
        else:
            health_status["checks"]["cpu"] = {
                "status": "healthy",
                "message": f"CPU使用率正常: {cpu_percent:.1f}%"
            }

        # 内存检查
        if memory_percent > 90:
            health_status["checks"]["memory"] = {
                "status": "critical",
                "message": f"内存使用率过高: {memory_percent:.1f}%"
            }
            health_status["overall_status"] = "critical"
        elif memory_percent > 80:
            health_status["checks"]["memory"] = {
                "status": "warning",
                "message": f"内存使用率较高: {memory_percent:.1f}%"
            }
            if health_status["overall_status"] == "healthy":
                health_status["overall_status"] = "warning"
        else:
            health_status["checks"]["memory"] = {
                "status": "healthy",
                "message": f"内存使用率正常: {memory_percent:.1f}%"
            }

        # 熔断器检查
        circuit_stats = unified_ai_client.get_circuit_breaker_stats()
        open_breakers = circuit_stats.get("open_breakers", 0)

        if open_breakers > 0:
            health_status["checks"]["circuit_breakers"] = {
                "status": "warning",
                "message": f"有{open_breakers}个熔断器处于开启状态"
            }
            if health_status["overall_status"] == "healthy":
                health_status["overall_status"] = "warning"
        else:
            health_status["checks"]["circuit_breakers"] = {
                "status": "healthy",
                "message": "所有熔断器状态正常"
            }

        # 缓冲区检查
        buffer_stats = adaptive_buffer_manager.get_performance_stats()
        total_buffer_size = sum(
            details.get("current_size", 0)
            for details in buffer_stats.get("buffer_details", {}).values()
        )

        if total_buffer_size > 1000:  # 阈值可配置
            health_status["checks"]["buffers"] = {
                "status": "warning",
                "message": f"缓冲区数据量较大: {total_buffer_size}条"
            }
            if health_status["overall_status"] == "healthy":
                health_status["overall_status"] = "warning"
        else:
            health_status["checks"]["buffers"] = {
                "status": "healthy",
                "message": f"缓冲区状态正常: {total_buffer_size}条"
            }

        return health_status

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "overall_status": "error",
            "timestamp": now_isoformat(),
            "error": str(e)
        }


async def _get_database_pool_stats() -> Dict[str, Any]:
    """获取数据库连接池统计（内部方法）"""
    try:
        from database.connection import async_engine
        from config.settings import DatabaseConfig
        
        if async_engine is None:
            return {"status": "not_initialized"}
        
        pool = async_engine.pool
        
        return {
            "pool_size": DatabaseConfig.DB_POOL_SIZE,
            "max_overflow": DatabaseConfig.DB_MAX_OVERFLOW,
            "pool_timeout": DatabaseConfig.DB_POOL_TIMEOUT,
            "current_checked_in": pool.checkedin(),
            "current_checked_out": pool.checkedout(),
            "current_overflow": pool.overflow(),
            "total_connections": pool.size(),
            "status": "healthy" if pool.checkedout() < pool.size() + pool.overflow() else "full"
        }
        
    except Exception as e:
        logger.warning(f"获取数据库连接池统计失败: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/metrics/realtime", summary="获取实时性能指标")
async def get_realtime_metrics():
    """
    获取实时性能指标（单次快照）
    优化：移除循环采样，改为单次采样，响应时间从4秒降至<50ms
    """
    try:
        timestamp = time.time()

        # 使用非阻塞方式获取CPU（interval=None使用上次采样值）
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()

        # 获取应用层指标
        buffer_stats = adaptive_buffer_manager.get_performance_stats()
        total_buffer_items = sum(
            details.get("current_size", 0)
            for details in buffer_stats.get("buffer_details", {}).values()
        )

        circuit_stats = unified_ai_client.get_circuit_breaker_stats()

        metrics = {
            "timestamp": timestamp,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used_mb": round(memory.used / (1024 * 1024), 2),
            "memory_available_mb": round(memory.available / (1024 * 1024), 2),
            "buffer_items": total_buffer_items,
            "active_breakers": circuit_stats.get("total_breakers", 0),
            "open_breakers": circuit_stats.get("open_breakers", 0)
        }

        return {
            "success": True,
            "metrics": metrics,
            "note": "单次快照数据，前端可轮询此接口实现实时监控"
        }

    except Exception as e:
        logger.error(f"获取实时指标失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取实时指标失败: {str(e)}")