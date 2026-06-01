"""APScheduler 持久化调度服务"""

import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from config.settings import DatabaseConfig, SchedulerConfig

logger = logging.getLogger(__name__)


class SchedulerService:
    """APScheduler 调度器封装（单例模式）"""
    _instance = None

    @classmethod
    def get_instance(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        jobstore = SQLAlchemyJobStore(
            url=DatabaseConfig.get_sync_database_url(),
            tablename="apscheduler_jobs",
        )
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": jobstore},
            job_defaults={
                "coalesce": SchedulerConfig.COALESCE,
                "max_instances": SchedulerConfig.MAX_INSTANCES,
                "misfire_grace_time": SchedulerConfig.MISFIRE_GRACE_TIME,
            },
        )
        self._started = False

    async def start(self):
        """启动调度器"""
        if self._started:
            return
        self.scheduler.start()
        self._started = True
        logger.info("APScheduler 调度器已启动")

    async def shutdown(self):
        """优雅关闭调度器"""
        if not self._started:
            return
        self.scheduler.shutdown(wait=True)
        self._started = False
        logger.info("APScheduler 调度器已关闭")

    def add_job(self, func, trigger, **kwargs):
        """添加调度任务"""
        return self.scheduler.add_job(func, trigger, **kwargs)

    def remove_job(self, job_id: str):
        """移除调度任务"""
        try:
            self.scheduler.remove_job(job_id)
        except Exception:
            pass  # 任务可能已不存在

    def remove_jobs_for_stream(self, stream_id: str):
        """移除某个视频流关联的所有调度任务"""
        for job in self.scheduler.get_jobs():
            if job.id.startswith(f"stream-{stream_id}"):
                self.scheduler.remove_job(job.id)
                logger.info(f"移除调度任务: {job.id}")

    def get_jobs(self) -> list:
        """获取所有调度任务"""
        return self.scheduler.get_jobs()

    async def recover_analysis_tasks(self):
        """系统启动时恢复所有 status=running 的分析任务"""
        from database.connection import DatabaseManager
        from models.analysis_task import AnalysisTaskDB, TaskStatusEnum
        from models.video_stream import VideoStreamDB
        from services.analysis_pipeline import AnalysisPipeline
        from sqlalchemy import select

        logger.info("开始恢复分析任务...")
        recovered = 0

        try:
            async with DatabaseManager.get_session() as session:
                # 查询所有 status=running 的任务
                result = await session.execute(
                    select(AnalysisTaskDB, VideoStreamDB.stream_url)
                    .join(VideoStreamDB, AnalysisTaskDB.stream_id == VideoStreamDB.id)
                    .where(AnalysisTaskDB.status == TaskStatusEnum.RUNNING)
                )
                tasks = result.all()

            pipeline = AnalysisPipeline.get_instance()
            for task, stream_url in tasks:
                try:
                    task_id = str(task.id)
                    prompt = task.prompt or "请分析画面中是否存在安全违规行为"
                    await pipeline.start_task(task_id, stream_url, prompt)
                    recovered += 1
                    logger.info(f"恢复分析任务: {task_id[:8]}")
                except Exception as e:
                    logger.warning(f"恢复任务失败 {str(task.id)[:8]}: {e}")

        except Exception as e:
            logger.error(f"任务恢复查询失败: {e}")

        logger.info(f"分析任务恢复完成: {recovered} 个任务已恢复")
        return recovered
