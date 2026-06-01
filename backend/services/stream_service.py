"""Video stream management service -- CRUD + mediamtx sync"""
import logging
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.video_stream import VideoStreamDB, VideoStreamCreate, VideoStreamUpdate
from services.mediamtx_client import MediaMTXClient
from config.settings import MediaMTXConfig

logger = logging.getLogger(__name__)


class StreamService:
    def __init__(self):
        self.mediamtx = MediaMTXClient()

    def _to_path_name(self, stream_id: uuid.UUID) -> str:
        """Convert stream UUID to mediamtx path name (safe characters only)."""
        return str(stream_id).replace("-", "")

    async def create(self, data: VideoStreamCreate, session: AsyncSession) -> VideoStreamDB:
        """Create stream in DB and register with mediamtx."""
        stream = VideoStreamDB(
            name=data.name,
            stream_url=data.stream_url,
            stream_type=data.stream_type,
            location=data.location,
            group_name=data.group_name,
            description=data.description,
            tags=data.tags or [],
        )
        session.add(stream)
        await session.flush()

        # Register with mediamtx (fire-and-log, per research anti-pattern guidance)
        path_name = self._to_path_name(stream.id)
        success = await self.mediamtx.add_path(path_name, data.stream_url)
        if not success:
            logger.warning(f"Stream {stream.id} created in DB but mediamtx registration failed")

        return stream

    async def get_by_id(self, stream_id: uuid.UUID, session: AsyncSession) -> Optional[VideoStreamDB]:
        result = await session.execute(
            select(VideoStreamDB).where(VideoStreamDB.id == stream_id)
        )
        return result.scalar_one_or_none()

    async def list_all(
        self, session: AsyncSession, skip: int = 0, limit: int = 50
    ) -> list[VideoStreamDB]:
        result = await session.execute(
            select(VideoStreamDB)
            .order_by(VideoStreamDB.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(
        self,
        stream_id: uuid.UUID,
        data: VideoStreamUpdate,
        session: AsyncSession,
    ) -> Optional[VideoStreamDB]:
        stream = await self.get_by_id(stream_id, session)
        if not stream:
            return None

        update_data = data.model_dump(exclude_unset=True)
        old_url = stream.stream_url

        for key, value in update_data.items():
            setattr(stream, key, value)

        await session.flush()

        # If stream_url changed, re-register with mediamtx
        if "stream_url" in update_data and update_data["stream_url"] != old_url:
            path_name = self._to_path_name(stream.id)
            await self.mediamtx.remove_path(path_name)
            await self.mediamtx.add_path(path_name, update_data["stream_url"])

        return stream

    async def delete(self, stream_id: uuid.UUID, session: AsyncSession) -> bool:
        """删除视频流，级联清理关联资源"""
        stream = await self.get_by_id(stream_id, session)
        if not stream:
            return False

        stream_id_str = str(stream_id)

        # 1. 停止运行中的分析任务
        try:
            from services.analysis_pipeline import AnalysisPipeline
            pipeline = AnalysisPipeline.get_instance()
            for task in pipeline.get_active_tasks():
                if task.get("stream_id") == stream_id_str:
                    await pipeline.stop_task(task["task_id"])
                    logger.info(f"停止关联分析任务: {task['task_id'][:8]}")
        except Exception as e:
            logger.warning(f"停止关联分析任务失败: {e}")

        # 2. 移除 APScheduler 中关联的调度任务
        try:
            from services.scheduler_service import SchedulerService
            scheduler = SchedulerService.get_instance()
            scheduler.remove_jobs_for_stream(stream_id_str)
        except Exception as e:
            logger.warning(f"移除调度任务失败: {e}")

        # 3. 清理 MinIO 帧截图（按 stream_id 前缀）
        try:
            from storage.services.minio_client import MinIOClient
            from config.settings import StorageConfig
            minio_client = MinIOClient()
            await minio_client.delete_by_prefix(
                StorageConfig.IMAGE_BUCKET, f"frames/{stream_id_str}/"
            )
            logger.info(f"清理 MinIO 帧截图: frames/{stream_id_str}/")
        except Exception as e:
            logger.warning(f"清理 MinIO 帧截图失败: {e}")

        # 4. Remove from mediamtx
        path_name = self._to_path_name(stream.id)
        await self.mediamtx.remove_path(path_name)

        # 5. 删除 DB 记录（CASCADE 自动清理 analysis_tasks 和 alerts）
        await session.delete(stream)
        await session.flush()
        return True

    async def sync_all_to_mediamtx(self, session: AsyncSession) -> int:
        """Re-register all streams with mediamtx. Called on startup."""
        streams = await self.list_all(session, skip=0, limit=1000)
        path_list = [
            {"name": self._to_path_name(s.id), "source_url": s.stream_url}
            for s in streams
        ]
        return await self.mediamtx.sync_all_paths(path_list)

    def get_hls_url(self, stream_id: uuid.UUID) -> str:
        """Get HLS playback URL for a stream."""
        path_name = self._to_path_name(stream_id)
        return MediaMTXConfig.get_hls_url(path_name)
