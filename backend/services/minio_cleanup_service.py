"""MinIO 帧截图定时清理服务"""

import logging
from config.settings import StorageConfig, SchedulerConfig
from storage.services.minio_client import MinIOClient

logger = logging.getLogger(__name__)


class MinIOCleanupService:
    """定时清理 MinIO 中过期的帧截图"""

    @staticmethod
    async def cleanup_expired_frames():
        """清理过期帧截图（由 APScheduler 定时触发）"""
        try:
            minio_client = MinIOClient()
            deleted = await minio_client.cleanup_expired_files(
                StorageConfig.IMAGE_BUCKET,
                max_age_days=SchedulerConfig.MINIO_RETENTION_DAYS,
            )
            logger.info(f"MinIO 定时清理完成: 删除 {deleted} 个过期文件")
            return deleted
        except Exception as e:
            logger.error(f"MinIO 定时清理失败: {e}")
            return 0

    @staticmethod
    def register_cleanup_job():
        """在 APScheduler 中注册定时清理任务"""
        from services.scheduler_service import SchedulerService

        scheduler = SchedulerService.get_instance()
        scheduler.add_job(
            MinIOCleanupService.cleanup_expired_frames,
            trigger="interval",
            hours=SchedulerConfig.MINIO_CLEANUP_INTERVAL_HOURS,
            id="minio-cleanup",
            name="MinIO 帧截图定时清理",
            replace_existing=True,
        )
        logger.info(
            f"MinIO 定时清理任务已注册（每 {SchedulerConfig.MINIO_CLEANUP_INTERVAL_HOURS} 小时执行）"
        )
