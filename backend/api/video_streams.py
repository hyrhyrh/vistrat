"""
视频流管理API路由（简化版）
提供基础的视频流管理功能，只处理必要字段
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from uuid import UUID
from datetime import datetime
from urllib.parse import quote
import logging
import asyncio

from services.video_stream_service import VideoStreamService
from utils.timezone_utils import now_isoformat

logger = logging.getLogger(__name__)
from models.video_stream import (
    VideoStreamCreate, VideoStreamUpdate, VideoStreamResponse,
    VideoStreamAnalysisTemplateCreate,
    StreamStatusEnum, StreamTypeEnum
)

from utils.websocket_manager import stream_health_ws_manager

router = APIRouter(prefix="/video-streams", tags=["视频流管理"])


async def _trigger_background_health_check(stream_ids: List):
    """后台健康检查任务（异步执行，不阻塞API响应）"""
    from utils.rtsp_health_checker import rtsp_health_checker

    logger.info(f"触发后台健康检查，流数量: {len(stream_ids)}")

    for stream_id in stream_ids:
        try:
            # 获取流信息
            stream = await VideoStreamService.get_stream_by_id(stream_id)
            if not stream or stream.stream_type != StreamTypeEnum.RTSP:
                continue

            # NOTE(async): RTSP 健康检查使用 OpenCV，是阻塞调用，必须在线程池中运行
            is_healthy, error_message, stream_info = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: rtsp_health_checker.check_rtsp_stream(
                    rtsp_url=stream.stream_url,
                    timeout=15  # 增加到15秒，匹配MJPEG流服务的超时设置
                )
            )

            # 构造健康数据
            health_data = {
                "health_status": "online" if is_healthy else "offline",
                "health_checked_at": now_isoformat(),
                "health_error_message": error_message if not is_healthy else None,
                "health_stream_info": stream_info if is_healthy else {}
            }

            # 通过WebSocket广播更新
            await stream_health_ws_manager.broadcast_health_status(str(stream_id), health_data)

            # 更新数据库状态
            new_status = StreamStatusEnum.ONLINE if is_healthy else StreamStatusEnum.OFFLINE
            if stream.status != new_status:
                await VideoStreamService.update_stream_status(stream_id, new_status)
                logger.info(f"更新流状态: {stream.name} -> {new_status.value}")

        except Exception as e:
            logger.error(f"后台健康检查失败 [stream_id={stream_id}]: {e}")


@router.get("/", summary="获取视频流列表(含ES统计，健康检查异步推送)")
async def get_streams(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    group_name: Optional[str] = Query(None, description="分组名称"),
    status: Optional[StreamStatusEnum] = Query(None, description="状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    include_statistics: bool = Query(True, description="是否包含ES统计信息"),
    trigger_health_check: bool = Query(False, description="触发后台健康检查（异步）")
):
    """
    获取视频流列表，支持分页和筛选

    集成功能:
    - Elasticsearch统计: 每个流的分析结果总数和告警总数
    - 健康状态: 返回数据库中的状态（ONLINE/OFFLINE）

    性能优化策略:
    - 立即返回数据库状态（毫秒级响应）
    - 后台异步执行RTSP健康检查（不阻塞响应）
    - 通过WebSocket实时推送检查结果到前端

    参数说明:
    - trigger_health_check=True: 触发后台异步健康检查
    """
    try:
        import asyncio
        from services.elasticsearch_service import elasticsearch_service
        from config.settings import ElasticsearchConfig
        from utils.rtsp_health_checker import rtsp_health_checker

        # 获取基础流列表
        streams = await VideoStreamService.get_streams(
            page=page,
            page_size=page_size,
            group_name=group_name,
            status=status,
            search=search
        )

        # 转换为字典以便添加额外字段
        streams_data = []

        # 定义单个流的处理函数
        async def process_stream(stream):
            stream_dict = stream.model_dump()
            tasks = []

            # ES统计查询 - 并发执行
            if include_statistics:
                async def get_frame_results_count():
                    try:
                        stream_id_str = str(stream.id)
                        query = {"term": {"stream_id": stream_id_str}}
                        count = await elasticsearch_service.count_documents(
                            index=ElasticsearchConfig.FRAME_RESULTS_INDEX,
                            query=query
                        )
                        return count
                    except Exception as e:
                        logger.warning(f"查询视频流 {stream.id} 分析结果总数失败: {e}")
                        return 0

                async def get_alerts_count():
                    try:
                        stream_id_str = str(stream.id)
                        query = {"term": {"stream_id": stream_id_str}}
                        count = await elasticsearch_service.count_documents(
                            index=ElasticsearchConfig.ALERTS_INDEX,
                            query=query
                        )
                        return count
                    except Exception as e:
                        logger.warning(f"查询视频流 {stream.id} 告警总数失败: {e}")
                        return 0

                tasks.append(get_frame_results_count())
                tasks.append(get_alerts_count())

            # 并发执行所有任务
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                stream_dict["total_analysis_count"] = results[0] if not isinstance(results[0], Exception) else 0
                stream_dict["total_alerts_count"] = results[1] if not isinstance(results[1], Exception) else 0

            return stream_dict

        # 并发处理所有流
        streams_data = await asyncio.gather(*[process_stream(stream) for stream in streams])

        # 触发后台健康检查（异步，不阻塞响应）
        if trigger_health_check:
            asyncio.create_task(_trigger_background_health_check([s.id for s in streams]))

        return streams_data

    except Exception as e:
        logger.error(f"获取视频流列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取视频流列表失败: {str(e)}")


@router.post("/", response_model=VideoStreamResponse, summary="创建视频流")
async def create_stream(stream_data: VideoStreamCreate):
    """创建新的视频流记录"""
    try:
        stream = await VideoStreamService.create_stream(stream_data)
        return stream
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建视频流失败: {str(e)}")


@router.get("/{stream_id}", response_model=VideoStreamResponse, summary="获取视频流详情")
async def get_stream(stream_id: UUID):
    """根据ID获取视频流详情"""
    try:
        stream = await VideoStreamService.get_stream_by_id(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        return stream
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频流详情失败: {str(e)}")


@router.put("/{stream_id}", response_model=VideoStreamResponse, summary="更新视频流")
async def update_stream(stream_id: UUID, stream_data: VideoStreamUpdate):
    """更新视频流信息"""
    try:
        stream = await VideoStreamService.update_stream(stream_id, stream_data)
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        return stream
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新视频流失败: {str(e)}")


@router.delete("/{stream_id}", summary="删除视频流")
async def delete_stream(stream_id: UUID):
    """删除视频流记录"""
    try:
        success = await VideoStreamService.delete_stream(stream_id)
        if not success:
            raise HTTPException(status_code=404, detail="视频流不存在")
        return {"message": "视频流删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除视频流失败: {str(e)}")


@router.patch("/{stream_id}/status", summary="更新流状态")
async def update_stream_status(stream_id: UUID, status: StreamStatusEnum):
    """更新视频流状态（在线/离线）"""
    try:
        success = await VideoStreamService.update_stream_status(stream_id, status)
        if not success:
            raise HTTPException(status_code=404, detail="视频流不存在")
        return {"message": f"流状态已更新为: {status.value}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新流状态失败: {str(e)}")


@router.get("/groups/{group_name}", response_model=List[VideoStreamResponse], summary="根据分组获取视频流")
async def get_streams_by_group(group_name: str):
    """根据分组名称获取视频流列表"""
    try:
        streams = await VideoStreamService.get_streams_by_group(group_name)
        return streams
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分组视频流失败: {str(e)}")


@router.get("/count/total", summary="获取视频流总数")
async def get_streams_count(
    group_name: Optional[str] = Query(None, description="分组名称"),
    status: Optional[StreamStatusEnum] = Query(None, description="状态筛选"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取视频流总数，支持筛选"""
    try:
        count = await VideoStreamService.get_streams_count(
            group_name=group_name,
            status=status,
            search=search
        )
        return {"total": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频流总数失败: {str(e)}")


@router.get("/statistics/summary", summary="获取流管理统计汇总")
async def get_statistics_summary():
    """获取视频流统计汇总信息"""
    try:
        # 获取所有流
        all_streams = await VideoStreamService.get_streams(page=1, page_size=1000)
        
        # 统计总数
        total_count = len(all_streams)
        
        # 按状态统计
        online_count = sum(1 for stream in all_streams if stream.status == StreamStatusEnum.ONLINE)
        offline_count = total_count - online_count
        
        # 按类型统计
        type_stats = {}
        for stream in all_streams:
            stream_type = stream.stream_type
            type_stats[stream_type] = type_stats.get(stream_type, 0) + 1
        
        # 按分组统计
        group_stats = {}
        for stream in all_streams:
            group_name = stream.group_name or "未分组"
            if group_name not in group_stats:
                group_stats[group_name] = {
                    "total": 0,
                    "online": 0,
                    "offline": 0
                }
            group_stats[group_name]["total"] += 1
            if stream.status == StreamStatusEnum.ONLINE:
                group_stats[group_name]["online"] += 1
            else:
                group_stats[group_name]["offline"] += 1
        
        # 计算在线率
        online_rate = round((online_count / total_count * 100), 1) if total_count > 0 else 0
        
        return {
            "success": True,
            "data": {
                "total_count": total_count,
                "online_count": online_count,
                "offline_count": offline_count,
                "online_rate": online_rate,
                "type_statistics": type_stats,
                "group_statistics": group_stats,
                "last_updated": now_isoformat()
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/{stream_id}/live-feed", summary="获取实时视频流信息")
async def get_live_feed(stream_id: UUID, request: Request):
    """获取视频流的实时播放信息"""
    try:
        stream = await VideoStreamService.get_stream_by_id(stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        # 检查流状态
        if stream.status != StreamStatusEnum.ONLINE:
            return {
                "status": "OFFLINE",
                "message": "视频流当前离线",
                "live_url": None,
                "rtsp_proxy_url": None,
                "mjpeg_stream_url": None
            }
        
        # 获取基础URL
        base_url = str(request.base_url).rstrip('/')
        original_url = stream.stream_url
        
        # 为不同流类型提供浏览器兼容的URL
        if stream.stream_type == StreamTypeEnum.RTSP or str(stream.stream_type).endswith("RTSP"):
            # RTSP流需要通过代理转换
            encoded_url = quote(original_url, safe='')
            
            # 提供多种播放方式
            rtsp_proxy_url = f"{base_url}/api/rtsp-proxy/?url={encoded_url}"
            mjpeg_stream_url = f"{base_url}/api/rtsp-proxy/stream?url={encoded_url}"
            
            return {
                "status": "ONLINE",
                "stream_type": stream.stream_type,
                "live_url": rtsp_proxy_url,  # 默认使用单帧代理
                "original_url": original_url,  # 原始RTSP URL
                "rtsp_proxy_url": rtsp_proxy_url,  # 单帧图片
                "mjpeg_stream_url": mjpeg_stream_url,  # MJPEG流
                "width": getattr(stream, 'width', None),
                "height": getattr(stream, 'height', None),
                "fps": getattr(stream, 'fps', None),
                "message": "视频流在线，已转换为浏览器兼容格式"
            }
        else:
            # 其他流类型直接返回原始URL
            return {
                "status": "ONLINE",
                "stream_type": stream.stream_type,
                "live_url": original_url,
                "original_url": original_url,
                "rtsp_proxy_url": None,
                "mjpeg_stream_url": None,
                "width": getattr(stream, 'width', None),
                "height": getattr(stream, 'height', None),
                "fps": getattr(stream, 'fps', None),
                "message": "视频流在线"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取实时流信息失败: {str(e)}")


@router.post("/{stream_id}/analysis/configure", summary="配置视频流分析算法")
async def configure_stream_analysis(stream_id: UUID, config_data: VideoStreamAnalysisTemplateCreate):
    """为视频流配置AI分析算法模板"""
    try:
        success = await VideoStreamService.configure_analysis_templates(
            str(stream_id), 
            config_data.template_ids,
            config_data.priority,
            config_data.confidence_threshold
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="配置视频流分析算法失败")
            
        return {
            "message": "视频流分析算法配置成功", 
            "stream_id": str(stream_id),
            "template_count": len(config_data.template_ids),
            "priority": config_data.priority,
            "confidence_threshold": config_data.confidence_threshold
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置视频流分析算法失败: {str(e)}")


@router.get("/{stream_id}/analysis/templates", summary="获取视频流分析模板")
async def get_stream_analysis_templates(stream_id: UUID):
    """获取视频流的分析模板配置"""
    try:
        result = await VideoStreamService.get_stream_analysis_templates(str(stream_id))
        
        if result is None:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分析模板失败: {str(e)}")


@router.post("/{stream_id}/analysis/start", summary="启动视频流分析")
async def start_stream_analysis(stream_id: UUID):
    """启动视频流的AI分析任务"""
    try:
        # 首先验证视频流是否存在
        stream = await VideoStreamService.get_stream_by_id(str(stream_id))
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
        
        logger.info(f"启动视频流分析: {stream.name} ({stream_id})")
        
        # 使用实时流分析服务
        from services.stream_analysis_service import stream_analysis_service
        
        result = await stream_analysis_service.start_stream_analysis(str(stream_id))
        
        return {
            "success": True,
            "message": "视频流分析已启动",
            "stream_id": str(stream_id),
            "stream_name": stream.name,
            "task_id": result.get('task_id'),
            "session_id": result.get('session_id'),
            "template_count": result.get('template_count', 0),
            "analysis_started_at": now_isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动视频流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.post("/{stream_id}/analysis/stop", summary="停止视频流分析")
async def stop_stream_analysis(stream_id: UUID):
    """停止视频流AI分析"""
    try:
        # 获取流信息
        stream = await VideoStreamService.get_stream_by_id(str(stream_id))
        if not stream:
            raise HTTPException(status_code=404, detail="视频流不存在")
            
        logger.info(f"停止视频流分析: {stream.name} ({stream_id})")
        
        # 使用实时流分析服务
        from services.stream_analysis_service import stream_analysis_service
        
        result = await stream_analysis_service.stop_stream_analysis(str(stream_id))
        
        return {
            "success": True,
            "message": "视频流分析已停止",
            "stream_id": str(stream_id),
            "task_id": result.get('task_id'),
            "frame_count": result.get('frame_count', 0),
            "alert_count": result.get('alert_count', 0),
            "analysis_stopped_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止视频流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止分析失败: {str(e)}")


@router.get("/{stream_id}/analysis/status", summary="获取视频流分析状态")
async def get_stream_analysis_status(stream_id: UUID):
    """获取视频流AI分析状态"""
    try:
        # 使用实时流分析服务
        from services.stream_analysis_service import stream_analysis_service
        
        status = await stream_analysis_service.get_stream_analysis_status(str(stream_id))
        
        return {
            "success": True,
            "stream_id": str(stream_id),
            "analysis_status": status
        }
        
    except Exception as e:
        logger.error(f"获取流分析状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")