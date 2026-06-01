"""v3 分析任务 API"""

import logging
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from database.connection import DatabaseManager
from models.analysis_task import AnalysisTaskDB, AnalysisTaskResponse, TaskStatusEnum
from models.video_stream import VideoStreamDB
from services.analysis_pipeline import AnalysisPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["v3-分析任务"])


class StartAnalysisRequest(BaseModel):
    """启动分析请求"""
    stream_id: str = Field(..., description="视频流ID")
    prompt: str = Field(
        default="请分析画面中是否存在安全违规行为",
        description="分析提示词",
    )
    config: Optional[Dict[str, Any]] = Field(None, description="额外配置")
    project_id: Optional[str] = Field(None, description="项目ID")


@router.post("/tasks/start")
async def start_analysis(request: StartAnalysisRequest):
    """启动分析任务"""
    # 查询视频流获取 stream_url
    async with DatabaseManager.get_session() as session:
        result = await session.execute(
            select(VideoStreamDB).where(VideoStreamDB.id == request.stream_id)
        )
        stream = result.scalar_one_or_none()
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")

        # 创建任务记录
        task = AnalysisTaskDB(
            id=uuid4(),
            stream_id=stream.id,
            status=TaskStatusEnum.PENDING,
            prompt=request.prompt,
            config=request.config or {},
            project_id=UUID(request.project_id) if request.project_id else None,
        )
        session.add(task)
        await session.flush()
        task_id = str(task.id)

    # 启动管线
    pipeline = AnalysisPipeline.get_instance()
    result = await pipeline.start_task(task_id, stream.stream_url, request.prompt)

    return {
        "task_id": task_id,
        "status": "running",
        "stream_id": request.stream_id,
    }


@router.post("/tasks/{task_id}/stop")
async def stop_analysis(task_id: str):
    """停止分析任务"""
    pipeline = AnalysisPipeline.get_instance()
    try:
        result = await pipeline.stop_task(task_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = None,
    stream_id: Optional[str] = None,
):
    """查询分析任务列表"""
    async with DatabaseManager.get_session() as session:
        query = select(AnalysisTaskDB).order_by(AnalysisTaskDB.created_at.desc())

        if status:
            query = query.where(AnalysisTaskDB.status == TaskStatusEnum(status))
        if stream_id:
            query = query.where(AnalysisTaskDB.stream_id == stream_id)

        result = await session.execute(query)
        tasks = result.scalars().all()

        return [
            AnalysisTaskResponse(
                id=str(t.id),
                stream_id=str(t.stream_id),
                status=t.status,
                prompt=t.prompt,
                config=t.config,
                started_at=t.started_at,
                stopped_at=t.stopped_at,
                created_at=t.created_at,
            )
            for t in tasks
        ]


@router.get("/tasks/active")
async def list_active_tasks():
    """查询活跃任务"""
    pipeline = AnalysisPipeline.get_instance()
    return pipeline.get_active_tasks()
