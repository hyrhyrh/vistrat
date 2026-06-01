"""
流监控管理API
基于FFmpeg + OpenCV的专业流媒体监控接口
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from pathlib import Path

from services.stream_monitor_service import stream_monitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream-monitor", tags=["流监控管理"])


@router.post("/start", summary="启动流监控服务")
async def start_monitoring():
    """启动整个流监控服务"""
    try:
        stream_monitor.start_monitoring()
        return {
            "success": True,
            "message": "流监控服务已启动",
            "status": stream_monitor.get_monitor_status()
        }
    except Exception as e:
        logger.error(f"启动流监控服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动服务失败: {str(e)}")


@router.post("/stop", summary="停止流监控服务")
async def stop_monitoring():
    """停止整个流监控服务"""
    try:
        stream_monitor.stop_monitoring()
        return {
            "success": True,
            "message": "流监控服务已停止"
        }
    except Exception as e:
        logger.error(f"停止流监控服务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止服务失败: {str(e)}")


@router.get("/status", summary="获取监控服务状态")
async def get_monitor_status():
    """获取流监控服务整体状态"""
    try:
        status = stream_monitor.get_monitor_status()
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取监控状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/stream/{stream_id}/hls/start", summary="启动HLS推流")
async def start_hls_stream(
    stream_id: str,
    rtsp_url: str = Query(..., description="RTSP流地址"),
    quality: str = Query("720p", description="输出质量", pattern="^(1080p|720p|480p|360p)$")
):
    """为指定流启动HLS推流"""
    try:
        result = stream_monitor.start_hls_stream(stream_id, rtsp_url, quality)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"HLS推流已启动: {stream_id}",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动HLS推流失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动推流失败: {str(e)}")


@router.post("/stream/{stream_id}/hls/stop", summary="停止HLS推流")
async def stop_hls_stream(stream_id: str):
    """停止指定流的HLS推流"""
    try:
        success = stream_monitor.stop_hls_stream(stream_id)
        
        if success:
            return {
                "success": True,
                "message": f"HLS推流已停止: {stream_id}"
            }
        else:
            return {
                "success": False,
                "message": f"流 {stream_id} 不存在或未在推流"
            }
            
    except Exception as e:
        logger.error(f"停止HLS推流失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止推流失败: {str(e)}")


@router.get("/stream/{stream_id}/status", summary="获取单个流状态")
async def get_stream_status(stream_id: str):
    """获取指定流的推流状态"""
    try:
        status = stream_monitor.get_stream_status(stream_id)
        return {
            "success": True,
            "data": status
        }
    except Exception as e:
        logger.error(f"获取流状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/stream/{stream_id}/health", summary="检查流健康状态")
async def check_stream_health(
    stream_id: str,
    rtsp_url: str = Query(..., description="RTSP流地址")
):
    """实时检查指定流的健康状态"""
    try:
        health_result = stream_monitor.check_stream_health_now(rtsp_url)
        return {
            "success": True,
            "stream_id": stream_id,
            "data": health_result
        }
    except Exception as e:
        logger.error(f"检查流健康状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@router.get("/hls/{stream_id}/playlist.m3u8", summary="获取HLS播放列表")
async def get_hls_playlist(stream_id: str):
    """获取指定流的HLS播放列表文件"""
    try:
        playlist_path = Path(f"/tmp/hls_streams/{stream_id}/playlist.m3u8")
        
        if not playlist_path.exists():
            raise HTTPException(status_code=404, detail=f"HLS流不存在: {stream_id}")
        
        return FileResponse(
            path=str(playlist_path),
            media_type="application/vnd.apple.mpegurl",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HLS播放列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取播放列表失败: {str(e)}")


@router.get("/hls/{stream_id}/{segment_name}", summary="获取HLS视频片段")
async def get_hls_segment(stream_id: str, segment_name: str):
    """获取HLS视频片段文件"""
    try:
        # 安全检查文件名
        if not segment_name.endswith('.ts') and not segment_name.endswith('.m3u8'):
            raise HTTPException(status_code=400, detail="无效的文件类型")
        
        if '..' in segment_name or '/' in segment_name:
            raise HTTPException(status_code=400, detail="无效的文件名")
        
        segment_path = Path(f"/tmp/hls_streams/{stream_id}/{segment_name}")
        
        if not segment_path.exists():
            raise HTTPException(status_code=404, detail=f"视频片段不存在: {segment_name}")
        
        media_type = "video/mp2t" if segment_name.endswith('.ts') else "application/vnd.apple.mpegurl"
        
        return FileResponse(
            path=str(segment_path),
            media_type=media_type,
            headers={
                "Cache-Control": "max-age=10",
                "Access-Control-Allow-Origin": "*"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取HLS片段失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取片段失败: {str(e)}")


@router.get("/streams/summary", summary="获取所有流状态摘要")
async def get_streams_summary():
    """获取所有流的状态摘要"""
    try:
        monitor_status = stream_monitor.get_monitor_status()
        
        # 获取每个活跃流的详细状态
        stream_details = {}
        for stream_id in monitor_status["active_stream_ids"]:
            stream_details[stream_id] = stream_monitor.get_stream_status(stream_id)
        
        return {
            "success": True,
            "data": {
                "monitor_service": monitor_status,
                "streams": stream_details,
                "summary": {
                    "total_active_streams": monitor_status["active_streams"],
                    "service_running": monitor_status["running"],
                    "monitor_interval": monitor_status["monitor_interval"]
                }
            }
        }
    except Exception as e:
        logger.error(f"获取流摘要失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取摘要失败: {str(e)}")


@router.post("/streams/batch-health-check", summary="批量健康检查")
async def batch_health_check(background_tasks: BackgroundTasks):
    """对所有已配置的流进行批量健康检查"""
    try:
        def run_batch_check():
            """后台执行批量检查"""
            try:
                stream_monitor._check_all_streams()
                logger.info("批量健康检查完成")
            except Exception as e:
                logger.error(f"批量健康检查失败: {e}")
        
        # 添加后台任务
        background_tasks.add_task(run_batch_check)
        
        return {
            "success": True,
            "message": "批量健康检查已启动，将在后台执行"
        }
        
    except Exception as e:
        logger.error(f"启动批量健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动检查失败: {str(e)}")


@router.get("/config", summary="获取监控配置")
async def get_monitor_config():
    """获取当前监控配置"""
    return {
        "success": True,
        "config": {
            "monitor_interval_seconds": stream_monitor.monitor_interval,
            "hls_output_directory": str(stream_monitor.ffmpeg_manager.hls_output_dir),
            "supported_qualities": ["1080p", "720p", "480p", "360p"],
            "default_quality": "720p",
            "hls_segment_duration": 2,
            "hls_playlist_size": 10
        }
    }


@router.put("/config", summary="更新监控配置")
async def update_monitor_config(
    monitor_interval: int = Query(30, ge=10, le=300, description="监控间隔（秒）")
):
    """更新监控配置"""
    try:
        stream_monitor.monitor_interval = monitor_interval
        
        return {
            "success": True,
            "message": "配置已更新",
            "new_config": {
                "monitor_interval_seconds": monitor_interval
            }
        }
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")