"""分析管线编排器 — 管理 FrameExtractor + AnalysisService 生命周期"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from config.settings import FrameConfig
from database.connection import DatabaseManager
from models.analysis_task import AnalysisTaskDB, TaskStatusEnum
from services.frame_extractor import FrameExtractor
from services.analysis_service import AnalysisService
from services.ai_client import AIAnalysisClient

logger = logging.getLogger(__name__)


@dataclass
class _RunningTask:
    """运行中的分析任务"""
    task_id: str
    stream_url: str
    stream_id: str  # 视频流 ID（用于告警生成和级联清理）
    queue: asyncio.Queue
    extractor: FrameExtractor
    analyzer: AnalysisService
    extractor_task: asyncio.Task
    analyzer_task: asyncio.Task


class AnalysisPipeline:
    """管理多个分析任务的生命周期"""
    _instance = None

    @classmethod
    def get_instance(cls) -> "AnalysisPipeline":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._tasks: dict[str, _RunningTask] = {}
        self._ai_client = AIAnalysisClient()
        self._lock = asyncio.Lock()

    async def start_task(self, task_id: str, stream_url: str, prompt: str) -> dict:
        """启动分析任务"""
        async with self._lock:
            if task_id in self._tasks:
                raise ValueError(f"任务已在运行中: {task_id}")

            # 获取 stream_id（用于告警生成和级联清理）
            stream_id_str = ""
            try:
                async with DatabaseManager.get_session() as session:
                    task_obj = await session.get(AnalysisTaskDB, task_id)
                    if task_obj and task_obj.stream_id:
                        stream_id_str = str(task_obj.stream_id)
            except Exception:
                pass

            # 创建队列连接生产者和消费者
            queue = asyncio.Queue(maxsize=FrameConfig.FRAME_QUEUE_MAXSIZE)

            # 创建帧提取器和分析服务
            extractor = FrameExtractor(stream_url, queue, task_id)
            analyzer = AnalysisService(queue, self._ai_client, stream_id=stream_id_str or None)

            # 启动异步任务
            extractor_task = asyncio.create_task(
                extractor.run(), name=f"extractor-{task_id[:8]}"
            )
            analyzer_task = asyncio.create_task(
                analyzer.run(prompt), name=f"analyzer-{task_id[:8]}"
            )

            # 更新数据库状态
            try:
                async with DatabaseManager.get_session() as session:
                    from sqlalchemy import update
                    await session.execute(
                        update(AnalysisTaskDB)
                        .where(AnalysisTaskDB.id == task_id)
                        .values(
                            status=TaskStatusEnum.RUNNING,
                            started_at=datetime.now(timezone.utc),
                        )
                    )
            except Exception as e:
                logger.warning(f"更新任务状态失败（不阻塞启动）: {e}")

            # 注册运行中的任务
            self._tasks[task_id] = _RunningTask(
                task_id=task_id,
                stream_url=stream_url,
                stream_id=stream_id_str,
                queue=queue,
                extractor=extractor,
                analyzer=analyzer,
                extractor_task=extractor_task,
                analyzer_task=analyzer_task,
            )

            logger.info(f"分析任务启动: task={task_id[:8]}, stream={stream_url}")
            return {"task_id": task_id, "status": "running"}

    async def stop_task(self, task_id: str) -> dict:
        """停止分析任务"""
        async with self._lock:
            running = self._tasks.pop(task_id, None)
            if running is None:
                raise ValueError(f"任务未在运行: {task_id}")

        # 停止帧提取器和分析服务
        await running.extractor.stop()
        await running.analyzer.stop()

        # 取消异步任务
        running.extractor_task.cancel()
        running.analyzer_task.cancel()
        await asyncio.gather(
            running.extractor_task, running.analyzer_task, return_exceptions=True
        )

        # 更新数据库状态
        try:
            async with DatabaseManager.get_session() as session:
                from sqlalchemy import update
                await session.execute(
                    update(AnalysisTaskDB)
                    .where(AnalysisTaskDB.id == task_id)
                    .values(
                        status=TaskStatusEnum.STOPPED,
                        stopped_at=datetime.now(timezone.utc),
                    )
                )
        except Exception as e:
            logger.warning(f"更新任务状态失败: {e}")

        stats = running.analyzer.stats
        logger.info(f"分析任务停止: task={task_id[:8]}, stats={stats}")
        return {"task_id": task_id, "status": "stopped", "stats": stats}

    async def stop_all(self):
        """停止所有任务（应用关闭时调用）"""
        task_ids = list(self._tasks.keys())
        for task_id in task_ids:
            try:
                await self.stop_task(task_id)
            except Exception as e:
                logger.error(f"停止任务失败 {task_id[:8]}: {e}")

        # 关闭AI客户端
        await self._ai_client.close()
        logger.info("分析管线已完全关闭")

    def get_active_tasks(self) -> list[dict]:
        """返回活跃任务列表"""
        return [
            {"task_id": t.task_id, "stream_url": t.stream_url, "stream_id": t.stream_id}
            for t in self._tasks.values()
        ]

    def get_active_count(self) -> int:
        """返回活跃任务数量"""
        return len(self._tasks)

    def get_ffmpeg_process_count(self) -> int:
        """返回存活的ffmpeg进程数"""
        return sum(
            1 for t in self._tasks.values()
            if hasattr(t.extractor, 'decoder') and t.extractor.decoder.is_alive()
        )
