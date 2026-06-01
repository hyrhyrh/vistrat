"""Video stream CRUD API -- /api/v3/streams/"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_async_session
from models.video_stream import VideoStreamCreate, VideoStreamUpdate, VideoStreamResponse
from services.stream_service import StreamService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/streams", tags=["streams"])

# Module-level service instance
stream_service = StreamService()


@router.get("/", response_model=list[VideoStreamResponse])
async def list_streams(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """List all video streams"""
    streams = await stream_service.list_all(session, skip=skip, limit=limit)
    results = []
    for s in streams:
        resp = _to_response(s)
        results.append(resp)
    return results


@router.post("/", response_model=VideoStreamResponse, status_code=201)
async def create_stream(
    data: VideoStreamCreate,
    session: AsyncSession = Depends(get_async_session),
):
    """Create video stream and register with mediamtx"""
    stream = await stream_service.create(data, session)
    return _to_response(stream)


@router.get("/{stream_id}", response_model=VideoStreamResponse)
async def get_stream(
    stream_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Get single video stream details"""
    stream = await stream_service.get_by_id(stream_id, session)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _to_response(stream)


@router.put("/{stream_id}", response_model=VideoStreamResponse)
async def update_stream(
    stream_id: uuid.UUID,
    data: VideoStreamUpdate,
    session: AsyncSession = Depends(get_async_session),
):
    """Update video stream (re-registers mediamtx if URL changed)"""
    stream = await stream_service.update(stream_id, data, session)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    return _to_response(stream)


@router.delete("/{stream_id}", status_code=204)
async def delete_stream(
    stream_id: uuid.UUID,
    session: AsyncSession = Depends(get_async_session),
):
    """Delete video stream and unregister from mediamtx"""
    deleted = await stream_service.delete(stream_id, session)
    if not deleted:
        raise HTTPException(status_code=404, detail="Stream not found")


def _to_response(stream) -> dict:
    """Convert ORM model to response dict with hls_url."""
    return {
        "id": str(stream.id),
        "name": stream.name,
        "stream_url": stream.stream_url,
        "stream_type": stream.stream_type,
        "location": stream.location,
        "group_name": stream.group_name,
        "description": stream.description,
        "tags": stream.tags or [],
        "status": stream.status,
        "created_at": stream.created_at,
        "updated_at": stream.updated_at,
        "hls_url": stream_service.get_hls_url(stream.id),
    }
