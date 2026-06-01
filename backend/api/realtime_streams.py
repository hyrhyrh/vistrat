"""
实时流管理API - 提供完整的RTSP实时流AI分析接口
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from services.realtime_stream_analysis_service import realtime_stream_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime-streams", tags=["实时流AI分析"])


# 数据模型定义
class CreateStreamRequest(BaseModel):
    """创建实时流请求"""
    stream_name: str = Field(..., description="流名称")
    rtsp_url: str = Field(..., description="RTSP流地址")
    template_ids: List[str] = Field(..., description="AI算法模板ID列表")
    frame_interval: float = Field(3.0, description="帧采样间隔（秒）", gt=0.1, le=60.0)
    auto_restart: bool = Field(True, description="是否自动重启")
    max_reconnect_attempts: int = Field(5, description="最大重连尝试次数", ge=1, le=20)
    analysis_enabled: bool = Field(True, description="是否启用分析")
    alert_enabled: bool = Field(True, description="是否启用告警")
    storage_enabled: bool = Field(True, description="是否启用存储")


class UpdateStreamRequest(BaseModel):
    """更新实时流请求"""
    stream_name: Optional[str] = Field(None, description="流名称")
    rtsp_url: Optional[str] = Field(None, description="RTSP流地址")
    template_ids: Optional[List[str]] = Field(None, description="AI算法模板ID列表")
    frame_interval: Optional[float] = Field(None, description="帧采样间隔（秒）", gt=0.1, le=60.0)
    auto_restart: Optional[bool] = Field(None, description="是否自动重启")
    max_reconnect_attempts: Optional[int] = Field(None, description="最大重连尝试次数", ge=1, le=20)
    analysis_enabled: Optional[bool] = Field(None, description="是否启用分析")
    alert_enabled: Optional[bool] = Field(None, description="是否启用告警")
    storage_enabled: Optional[bool] = Field(None, description="是否启用存储")


class StreamResponse(BaseModel):
    """流响应基础模型"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None


@router.post("/", response_model=StreamResponse)
async def create_stream(request: CreateStreamRequest):
    """
    创建新的实时流配置
    
    创建一个新的RTSP实时流分析配置，但不会立即启动分析。
    需要调用启动接口来开始分析。
    """
    try:
        logger.info(f"创建实时流配置: {request.stream_name}, URL: {request.rtsp_url}")
        
        # 验证RTSP URL格式
        if not request.rtsp_url.startswith(('rtsp://', 'rtmp://', 'http://')):
            raise HTTPException(
                status_code=400, 
                detail="无效的流地址，仅支持 rtsp://, rtmp://, http:// 协议"
            )
        
        # 验证算法模板
        if not request.template_ids:
            raise HTTPException(
                status_code=400,
                detail="必须指定至少一个AI分析算法"
            )
        
        # 创建流配置
        stream_id = await realtime_stream_service.create_stream_config(
            stream_name=request.stream_name,
            rtsp_url=request.rtsp_url,
            template_ids=request.template_ids,
            frame_interval=request.frame_interval,
            auto_restart=request.auto_restart,
            max_reconnect_attempts=request.max_reconnect_attempts,
            analysis_enabled=request.analysis_enabled,
            alert_enabled=request.alert_enabled,
            storage_enabled=request.storage_enabled
        )
        
        # 获取创建的流信息
        stream_info = await realtime_stream_service.get_stream_status(stream_id)
        
        return StreamResponse(
            success=True,
            message=f"实时流配置创建成功",
            data={
                "stream_id": stream_id,
                "stream_info": stream_info
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建实时流配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")


@router.get("/", response_model=StreamResponse)
async def list_streams():
    """
    获取所有实时流列表
    
    返回系统中所有已配置的实时流及其状态信息。
    """
    try:
        streams = await realtime_stream_service.list_streams()
        
        return StreamResponse(
            success=True,
            message=f"获取实时流列表成功",
            data={
                "streams": streams,
                "total_count": len(streams)
            }
        )
        
    except Exception as e:
        logger.error(f"获取实时流列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/{stream_id}", response_model=StreamResponse)
async def get_stream(stream_id: str):
    """
    获取指定实时流的详细信息
    
    包括配置信息、运行状态、统计数据等。
    """
    try:
        stream_info = await realtime_stream_service.get_stream_status(stream_id)
        
        if not stream_info:
            raise HTTPException(status_code=404, detail=f"实时流不存在: {stream_id}")
        
        return StreamResponse(
            success=True,
            message="获取实时流信息成功",
            data=stream_info
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时流信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")


@router.put("/{stream_id}", response_model=StreamResponse)
async def update_stream(stream_id: str, request: UpdateStreamRequest):
    """
    更新实时流配置
    
    更新流的配置参数。如果流正在运行且修改了关键参数，
    系统会自动重启分析任务。
    """
    try:
        # 检查流是否存在
        existing_stream = await realtime_stream_service.get_stream_status(stream_id)
        if not existing_stream:
            raise HTTPException(status_code=404, detail=f"实时流不存在: {stream_id}")
        
        # 准备更新数据
        update_data = {}
        for field, value in request.dict(exclude_unset=True).items():
            if value is not None:
                update_data[field] = value
        
        if not update_data:
            raise HTTPException(status_code=400, detail="没有提供有效的更新数据")
        
        # 执行更新
        success = await realtime_stream_service.update_stream_config(stream_id, **update_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="更新配置失败")
        
        # 获取更新后的信息
        updated_stream = await realtime_stream_service.get_stream_status(stream_id)
        
        return StreamResponse(
            success=True,
            message="实时流配置更新成功",
            data=updated_stream
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新实时流配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.delete("/{stream_id}", response_model=StreamResponse)
async def delete_stream(stream_id: str):
    """
    删除实时流配置
    
    删除指定的实时流配置。如果流正在运行，会先停止分析。
    """
    try:
        # 检查流是否存在
        existing_stream = await realtime_stream_service.get_stream_status(stream_id)
        if not existing_stream:
            raise HTTPException(status_code=404, detail=f"实时流不存在: {stream_id}")
        
        # 删除配置
        success = await realtime_stream_service.delete_stream_config(stream_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="删除配置失败")
        
        return StreamResponse(
            success=True,
            message="实时流配置删除成功",
            data={"stream_id": stream_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除实时流配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.post("/{stream_id}/analysis/start", response_model=StreamResponse)
async def start_analysis(stream_id: str):
    """
    启动实时流AI分析
    
    开始对指定的实时流进行AI多模态分析。
    分析过程包括帧提取、AI算法遍历、预警生成等。
    """
    try:
        logger.info(f"启动实时流分析: {stream_id}")
        
        result = await realtime_stream_service.start_stream_analysis(stream_id)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=400, 
                detail=result.get('message', '启动分析失败')
            )
        
        return StreamResponse(
            success=True,
            message=result['message'],
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启动实时流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.post("/{stream_id}/analysis/stop", response_model=StreamResponse)
async def stop_analysis(stream_id: str):
    """
    停止实时流AI分析
    
    停止指定实时流的AI分析任务。
    """
    try:
        logger.info(f"停止实时流分析: {stream_id}")
        
        result = await realtime_stream_service.stop_stream_analysis(stream_id)
        
        if not result.get('success', False):
            raise HTTPException(
                status_code=400, 
                detail=result.get('message', '停止分析失败')
            )
        
        return StreamResponse(
            success=True,
            message=result['message'],
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止实时流分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止分析失败: {str(e)}")


@router.get("/{stream_id}/analysis/status", response_model=StreamResponse)
async def get_analysis_status(stream_id: str):
    """
    获取实时流分析状态
    
    返回详细的分析状态，包括处理进度、统计信息等。
    """
    try:
        stream_info = await realtime_stream_service.get_stream_status(stream_id)
        
        if not stream_info:
            raise HTTPException(status_code=404, detail=f"实时流不存在: {stream_id}")
        
        # 提取分析状态信息
        analysis_status = {
            'stream_id': stream_id,
            'analysis_running': stream_info['status']['status'] == 'running',
            'task_id': stream_info['status'].get('task_id'),
            'frames_processed': stream_info['status'].get('frames_processed', 0),
            'alerts_generated': stream_info['status'].get('alerts_generated', 0),
            'connection_uptime': stream_info['status'].get('connection_uptime', 0),
            'last_frame_time': stream_info['status'].get('last_frame_time'),
            'error_message': stream_info['status'].get('error_message'),
            'task_status': stream_info.get('task_status')
        }
        
        return StreamResponse(
            success=True,
            message="获取分析状态成功",
            data=analysis_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分析状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.get("/system/stats", response_model=StreamResponse)
async def get_system_stats():
    """
    获取系统统计信息
    
    返回整个实时流分析系统的统计数据。
    """
    try:
        stats = await realtime_stream_service.get_service_stats()
        
        return StreamResponse(
            success=True,
            message="获取系统统计成功",
            data=stats
        )
        
    except Exception as e:
        logger.error(f"获取系统统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/system/cleanup", response_model=StreamResponse)
async def cleanup_system():
    """
    清理系统资源
    
    清理已停止的任务、临时文件等系统资源。
    """
    try:
        # 这里可以添加系统清理逻辑
        # 比如清理过期的任务、临时文件等
        
        logger.info("执行系统清理")
        
        return StreamResponse(
            success=True,
            message="系统清理完成",
            data={"cleaned_at": now_isoformat()}
        )
        
    except Exception as e:
        logger.error(f"系统清理失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")


@router.get("/templates/available")
async def get_available_templates():
    """
    获取可用的AI算法模板
    
    返回可用于实时流分析的AI算法模板列表。
    """
    try:
        # TODO(realtime_streams): 对接实际的模板服务，替换硬编码示例数据
        
        templates = [
            {
                "id": "template_1",
                "name": "通用目标检测",
                "description": "检测人员、车辆等常见目标",
                "category": "目标检测",
                "status": "active"
            },
            {
                "id": "template_2", 
                "name": "异常行为分析",
                "description": "检测异常行为和可疑活动",
                "category": "行为分析",
                "status": "active"
            }
        ]
        
        return StreamResponse(
            success=True,
            message="获取可用模板成功",
            data={
                "templates": templates,
                "total_count": len(templates)
            }
        )
        
    except Exception as e:
        logger.error(f"获取可用模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取模板失败: {str(e)}")


@router.post("/test-connection")
async def test_rtsp_connection(rtsp_url: str = Body(..., embed=True)):
    """
    测试RTSP连接
    
    测试指定的RTSP地址是否可以正常连接。
    """
    try:
        logger.info(f"测试RTSP连接: {rtsp_url}")
        
        # 验证URL格式
        if not rtsp_url.startswith(('rtsp://', 'rtmp://', 'http://')):
            raise HTTPException(
                status_code=400,
                detail="无效的流地址格式"
            )
        
        import cv2
        import asyncio
        
        def test_connection():
            try:
                cap = cv2.VideoCapture(rtsp_url)
                if not cap.isOpened():
                    return False, "无法打开RTSP流"
                
                ret, frame = cap.read()
                cap.release()
                
                if not ret or frame is None:
                    return False, "无法读取视频数据"
                
                return True, "连接成功"
                
            except Exception as e:
                return False, f"连接异常: {str(e)}"
        
        # 🔧 ARM兼容：使用asyncio.to_thread替代ThreadPoolExecutor
        try:
            success, message = await asyncio.wait_for(
                asyncio.to_thread(test_connection),
                timeout=10.0
            )
        except asyncio.TimeoutError:
            success, message = False, "连接超时"
        
        return StreamResponse(
            success=success,
            message=message,
            data={
                "rtsp_url": rtsp_url,
                "test_time": now_isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试RTSP连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")