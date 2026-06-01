"""系统健康检查服务"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class HealthService:
    """系统组件健康检查"""

    @staticmethod
    async def check() -> dict:
        """检查所有系统组件状态"""
        from database.connection import DatabaseManager
        from config.settings import MediaMTXConfig, RedisConfig

        # 数据库检查
        db_ok = False
        try:
            db_ok = await DatabaseManager.test_connection()
        except Exception:
            db_ok = False

        # Redis检查
        redis_ok = False
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(RedisConfig.get_redis_url(), socket_timeout=3)
            redis_ok = await r.ping()
            await r.aclose()
        except Exception:
            redis_ok = False

        # mediamtx检查
        mediamtx_ok = False
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{MediaMTXConfig.get_api_url()}/v3/paths/list")
                mediamtx_ok = resp.status_code == 200
        except Exception:
            mediamtx_ok = False

        # 活跃任务和ffmpeg进程
        from services.analysis_pipeline import AnalysisPipeline
        pipeline = AnalysisPipeline.get_instance()

        components = {
            "database": db_ok,
            "redis": redis_ok,
            "mediamtx": mediamtx_ok,
            "active_tasks": pipeline.get_active_count(),
            "ffmpeg_processes": pipeline.get_ffmpeg_process_count(),
        }

        # 综合状态判断
        overall = "healthy"
        if not db_ok:
            overall = "unhealthy"
        elif not redis_ok or not mediamtx_ok:
            overall = "degraded"

        return {
            "status": overall,
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
