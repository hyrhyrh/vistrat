"""
向后兼容的video API路由
将旧的 /api/video/* 路径代理到新的统一视频管理API
保持前端代码的兼容性，避免破坏性变更
"""

from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional

from .video_files import upload_video, get_video_file, stream_video_by_id

router = APIRouter(prefix="/video", tags=["视频-兼容性接口"])

# 代理到统一的视频管理API
@router.post("/upload", summary="上传视频文件 (兼容性接口)")
async def video_upload_compat(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """兼容性接口：上传视频文件，代理到 /api/video-files/upload"""
    return await upload_video(file, name, description, tags)


@router.get("/files/{filename}", summary="获取视频文件 (兼容性接口)")
@router.head("/files/{filename}")
async def video_files_compat(filename: str):
    """兼容性接口：获取视频文件，代理到 /api/video-files/files/{filename}"""
    return await get_video_file(filename)


@router.get("/stream/{video_id}", summary="流式播放视频 (兼容性接口)")
async def video_stream_compat(video_id: str):
    """兼容性接口：流式播放视频，代理到 /api/video-files/stream/{video_id}"""
    return await stream_video_by_id(video_id)