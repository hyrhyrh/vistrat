"""
视频流管理API路由
处理实时RTSP/WebRTC视频流的管理、监控、分析等功能

【架构兼容】统一使用同步psycopg + ThreadPool，避免greenlet/thread问题
"""

import logging
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from database.connection import DatabaseManager
from models.video_metadata import VideoMetadata, VideoType, VideoStatus
from streams.services.stream_manager import StreamManager
from prompts.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/streams", tags=["streams"])

# 初始化服务
stream_manager = StreamManager()
prompt_manager = PromptManager()


class StreamCreateRequest(BaseModel):
    """创建流请求"""
    name: str
    stream_url: str
    stream_type: str = "rtsp"  # rtsp, webrtc, hls
    description: Optional[str] = None
    tags: List[str] = []


class StreamUpdateRequest(BaseModel):
    """更新流请求"""
    name: Optional[str] = None
    stream_url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    enabled: Optional[bool] = None


@router.get("/list")
async def list_streams():
    """获取视频流列表(包含ES统计信息)"""
    try:
        from services.elasticsearch_service import elasticsearch_service
        from config.settings import ElasticsearchConfig

        streams = await stream_manager.get_stream_list()
        streams_data = []

        for stream in streams:
            stream_dict = stream.model_dump()

            # 查询该视频流的分析结果总数(video_frame_results)
            try:
                frame_results_count = await elasticsearch_service.count_documents(
                    index=ElasticsearchConfig.FRAME_RESULTS_INDEX,
                    query={"term": {"video_id": str(stream.id)}}
                )
                stream_dict["total_analysis_count"] = frame_results_count
            except Exception as e:
                logger.warning(f"查询视频流 {stream.id} 分析结果总数失败: {e}")
                stream_dict["total_analysis_count"] = 0

            # 查询该视频流的告警总数(video_alerts)
            try:
                alerts_count = await elasticsearch_service.count_documents(
                    index=ElasticsearchConfig.ALERTS_INDEX,
                    query={"term": {"video_id": str(stream.id)}}
                )
                stream_dict["total_alerts_count"] = alerts_count
            except Exception as e:
                logger.warning(f"查询视频流 {stream.id} 告警总数失败: {e}")
                stream_dict["total_alerts_count"] = 0

            streams_data.append(stream_dict)

        return {
            "status": "success",
            "data": streams_data,
            "total": len(streams_data)
        }
    except Exception as e:
        logger.error(f"获取视频流列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频流列表失败: {str(e)}")


@router.post("/create")
async def create_stream(request: StreamCreateRequest):
    """创建视频流"""
    try:
        stream = await stream_manager.create_stream(
            name=request.name,
            stream_url=request.stream_url,
            stream_type=request.stream_type,
            description=request.description,
            tags=request.tags
        )
        
        return {
            "status": "success",
            "message": "视频流创建成功",
            "data": stream.model_dump()
        }
    except Exception as e:
        logger.error(f"创建视频流失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建视频流失败: {str(e)}")


@router.get("/{stream_id}")
async def get_stream(stream_id: str):
    """获取视频流详情"""
    try:
        stream = await stream_manager.get_stream(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return {
            "status": "success",
            "data": stream.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取视频流详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频流详情失败: {str(e)}")


@router.put("/{stream_id}")
async def update_stream(stream_id: str, request: StreamUpdateRequest):
    """更新视频流"""
    try:
        stream = await stream_manager.update_stream(stream_id, request.model_dump(exclude_unset=True))
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return {
            "status": "success",
            "message": "视频流更新成功",
            "data": stream.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新视频流失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新视频流失败: {str(e)}")


@router.delete("/{stream_id}")
async def delete_stream(stream_id: str):
    """删除视频流"""
    try:
        success = await stream_manager.delete_stream(stream_id)
        if not success:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return {
            "status": "success",
            "message": "视频流删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除视频流失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除视频流失败: {str(e)}")


@router.post("/{stream_id}/start")
async def start_stream(stream_id: str):
    """启动视频流监控"""
    try:
        success = await stream_manager.start_stream(stream_id)
        if not success:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return {
            "status": "success",
            "message": "视频流已启动"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动视频流失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动视频流失败: {str(e)}")


@router.post("/{stream_id}/stop")
async def stop_stream(stream_id: str):
    """停止视频流监控"""
    try:
        success = await stream_manager.stop_stream(stream_id)
        if not success:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return {
            "status": "success",
            "message": "视频流已停止"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止视频流失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止视频流失败: {str(e)}")


@router.post("/{stream_id}/analyze")
async def start_stream_analysis(
    stream_id: str,
    prompt_template_ids: List[str],
    analysis_config: Optional[dict] = None
):
    """开始视频流分析"""
    try:
        # 获取视频流信息
        stream = await stream_manager.get_stream(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        # 验证提示词模板
        for template_id in prompt_template_ids:
            template = await prompt_manager.get_template(template_id)
            if not template:
                raise HTTPException(status_code=400, detail=f"提示词模板不存在: {template_id}")
        
        # 启动分析任务
        task_id = await stream_manager.start_analysis(
            stream_id=stream_id,
            prompt_template_ids=prompt_template_ids,
            analysis_config=analysis_config or {}
        )
        
        return {
            "status": "success",
            "message": "流分析任务已启动",
            "task_id": task_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动视频流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动视频流分析失败: {str(e)}")


@router.post("/{stream_id}/analysis/stop")
async def stop_stream_analysis(stream_id: str):
    """停止视频流分析"""
    try:
        success = await stream_manager.stop_analysis(stream_id)
        if not success:
            raise HTTPException(status_code=404, detail="未找到正在运行的分析任务")
        
        return {
            "status": "success",
            "message": "流分析任务已停止"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止流分析失败: {str(e)}")


@router.get("/{stream_id}/analysis/status")
async def get_stream_analysis_status(stream_id: str):
    """获取视频流分析状态"""
    try:
        status = await stream_manager.get_analysis_status(stream_id)
        if not status:
            raise HTTPException(status_code=404, detail="未找到分析任务")
        
        return {
            "status": "success",
            "data": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取流分析状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取流分析状态失败: {str(e)}")


@router.get("/{stream_id}/analysis/results")
async def get_stream_analysis_results(stream_id: str, limit: int = 100):
    """获取视频流分析结果"""
    try:
        results = await stream_manager.get_analysis_results(stream_id, limit=limit)
        
        return {
            "status": "success",
            "data": results
        }
    except Exception as e:
        logger.error(f"获取流分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取流分析结果失败: {str(e)}")


@router.get("/{stream_id}/health")
async def check_stream_health(stream_id: str):
    """检查视频流RTSP健康状态"""
    try:
        from utils.rtsp_health_checker import rtsp_health_checker
        # 已使用 database.db_utils
        # asyncpg已替换为psycopg 3

        # 从数据库获取视频流信息（异步方式）
        async with DatabaseManager.get_session() as session:
            query = text("""
                SELECT id, name, rtsp_url, type FROM video_streams WHERE id = :stream_id
            """)
            result = await session.execute(query, {"stream_id": stream_id})
            row = result.first()
            stream_row = dict(row._mapping) if row else None

        if not stream_row:
            raise HTTPException(status_code=404, detail="视频流不存在")

        rtsp_url = stream_row['rtsp_url']
        stream_name = stream_row['name']
        stream_type = stream_row['type']

        try:

            # 如果是 RTSP 流,执行健康检查
            if stream_type == 'rtsp' and rtsp_url:
                is_healthy, error_message, stream_info = rtsp_health_checker.check_rtsp_stream(
                    rtsp_url=rtsp_url,
                    timeout=5  # 5秒超时
                )

                health_result = rtsp_health_checker.format_health_check_result(
                    is_healthy, error_message, stream_info
                )

                return {
                    "status": "success",
                    "data": {
                        "stream_id": stream_id,
                        "stream_name": stream_name,
                        "stream_type": stream_type,
                        "rtsp_url": rtsp_url,
                        "healthy": is_healthy,
                        "connection_status": "online" if is_healthy else "offline",
                        "error_message": error_message,
                        "stream_info": stream_info,
                        "suggestions": health_result.get('suggestions', [])
                    }
                }
            else:
                # 非 RTSP 流返回基本状态
                return {
                    "status": "success",
                    "data": {
                        "stream_id": stream_id,
                        "stream_name": stream_name,
                        "stream_type": stream_type,
                        "healthy": True,
                        "connection_status": "unknown",
                        "message": f"不支持对 {stream_type} 类型流进行健康检查"
                    }
                }

        except Exception as e:
            logger.error(f"健康检查执行失败: {e}")
            raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检查流健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"检查流健康状态失败: {str(e)}")


@router.get("/statistics/overview")
async def get_stream_statistics():
    """获取视频流统计信息"""
    try:
        stats = await stream_manager.get_statistics()
        
        return {
            "status": "success",
            "data": stats
        }
    except Exception as e:
        logger.error(f"获取流统计信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取流统计信息失败: {str(e)}")


@router.websocket("/{stream_id}/feed")
async def websocket_stream_feed(websocket: WebSocket, stream_id: str):
    """视频流WebSocket端点"""
    await websocket.accept()
    try:
        # 注册WebSocket连接到流管理器
        await stream_manager.register_websocket(stream_id, websocket)
        
        while True:
            # 等待客户端消息或保持连接
            message = await websocket.receive_text()
            # 可以处理客户端发送的控制消息
            
    except WebSocketDisconnect:
        logger.info(f"视频流 {stream_id} WebSocket连接已断开")
    except Exception as e:
        logger.error(f"视频流 {stream_id} WebSocket连接异常: {e}")
    finally:
        # 注销WebSocket连接
        await stream_manager.unregister_websocket(stream_id, websocket)