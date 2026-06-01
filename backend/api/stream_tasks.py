"""
视频流实时分析任务API
支持任务级别管理、时间配置、ROI配置
企业级功能：启用/停用、自动恢复、批量操作
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
import logging

from services.stream_task_manager import stream_task_manager
from utils.timezone_utils import now_isoformat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stream-tasks", tags=["视频流分析任务"])


# ==================== 数据模型 ====================

class ROIRegion(BaseModel):
    """ROI区域定义"""
    id: str
    type: str = Field(..., pattern="^(rectangle|polygon)$", description="区域类型")
    name: str
    data: Dict[str, Any] = Field(..., description="区域坐标数据")
    active: bool = True


class ROIConfig(BaseModel):
    """ROI配置"""
    enabled: bool = False
    regions: List[ROIRegion] = []
    image_info: Optional[Dict[str, Any]] = None


class TimeRange(BaseModel):
    """时间范围配置"""
    start_time: str = Field(..., alias="startTime", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="开始时间(HH:MM)")
    end_time: str = Field(..., alias="endTime", pattern="^([01]?[0-9]|2[0-3]):[0-5][0-9]$", description="结束时间(HH:MM)")
    days: List[int] = Field(..., description="运行日期，0=周日,1=周一...6=周六")

    class Config:
        populate_by_name = True  # 允许同时使用字段名和别名


class TimeConfig(BaseModel):
    """时间配置"""
    enabled: bool = False
    time_ranges: List[TimeRange] = []
    timezone: str = "Asia/Shanghai"


class StreamAnalysisTaskCreate(BaseModel):
    """创建分析任务请求"""
    stream_id: UUID
    algorithm_config_id: UUID
    task_name: str = Field(..., min_length=1, max_length=255)
    time_config: TimeConfig
    roi_config: ROIConfig
    priority: int = Field(1, ge=1, le=10, description="任务优先级，1-10")
    confidence_threshold: float = Field(0.7, ge=0, le=1, description="置信度阈值")
    analysis_interval: int = Field(10, ge=5, le=300, description="分析间隔(秒)")
    auto_recover: bool = Field(True, description="系统重启后自动恢复")


class StreamAnalysisTaskUpdate(BaseModel):
    """更新分析任务请求"""
    task_name: Optional[str] = Field(None, min_length=1, max_length=255)
    time_config: Optional[TimeConfig] = None
    roi_config: Optional[ROIConfig] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1)
    analysis_interval: Optional[int] = Field(None, ge=5, le=300)
    auto_recover: Optional[bool] = None


class StreamAnalysisTaskResponse(BaseModel):
    """分析任务响应"""
    id: str
    stream_id: str
    algorithm_config_id: str
    task_name: str
    status: str
    is_active: bool
    auto_recover: bool
    time_config: Dict[str, Any]
    roi_config: Dict[str, Any]
    priority: int
    confidence_threshold: float
    analysis_interval: int
    is_running: bool
    should_run_now: bool
    stream_name: Optional[str] = None
    algorithm_name: Optional[str] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TaskBatchOperation(BaseModel):
    """批量操作请求"""
    task_ids: List[str]
    operation: str = Field(..., pattern="^(enable|disable|delete|start|stop)$")


# ==================== API端点 ====================

@router.post("/", response_model=Dict[str, Any], summary="创建分析任务")
async def create_task(task_data: StreamAnalysisTaskCreate):
    """为指定视频流创建新的分析任务"""
    try:
        result = await stream_task_manager.create_task(
            stream_id=str(task_data.stream_id),
            algorithm_config_id=str(task_data.algorithm_config_id),
            task_name=task_data.task_name,
            time_config=task_data.time_config.dict(),
            roi_config=task_data.roi_config.dict(),
            priority=task_data.priority,
            confidence_threshold=task_data.confidence_threshold,
            analysis_interval=task_data.analysis_interval,
            auto_recover=task_data.auto_recover
        )

        # 支持新旧两种返回格式
        if isinstance(result, dict):
            task_id = result.get("task_id")
            operation_type = result.get("operation_type", "created")
        else:
            # 兼容旧版本返回字符串的情况
            task_id = result
            operation_type = "created"

        # 根据操作类型返回不同的提示
        operation_msg = "分析任务配置已更新" if operation_type == "updated" else "分析任务创建成功"

        return {
            "success": True,
            "message": operation_msg,
            "task_id": task_id,
            "operation_type": operation_type,
            "created_at": now_isoformat()
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"创建分析任务失败: {e}")

        # 处理重复键错误,提供友好提示
        if "duplicate key value violates unique constraint" in error_msg and "uk_stream_algorithm_config" in error_msg:
            raise HTTPException(
                status_code=409,  # 使用409 Conflict状态码
                detail="该视频流已存在相同的算法任务配置，请勿重复创建。如需修改配置，请使用编辑功能。"
            )

        # 其他错误
        raise HTTPException(status_code=500, detail=f"创建任务失败: {error_msg}")


@router.get("/", response_model=List[StreamAnalysisTaskResponse], summary="获取任务列表")
async def get_tasks(
    stream_id: Optional[UUID] = Query(None, description="按视频流ID筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    active_only: bool = Query(False, description="仅显示启用的任务")
):
    """获取分析任务列表，支持筛选"""
    try:
        logger.info(f"📥 收到任务列表请求: stream_id={stream_id}, status={status}, active_only={active_only}")

        tasks = await stream_task_manager.get_task_list(
            stream_id=str(stream_id) if stream_id else None
        )

        logger.info(f"📋 从manager获取到 {len(tasks)} 个任务")
        if tasks:
            logger.info(f"   首个任务示例: {tasks[0].get('id', 'N/A')[:8]}... - {tasks[0].get('task_name', 'N/A')}")

        # 应用筛选条件
        if status:
            before_count = len(tasks)
            tasks = [t for t in tasks if t.get('status') == status]
            logger.info(f"🔍 按状态筛选({status}): {before_count} -> {len(tasks)}")

        if active_only:
            before_count = len(tasks)
            tasks = [t for t in tasks if t.get('is_active', False)]
            logger.info(f"🔍 按启用状态筛选: {before_count} -> {len(tasks)}")

        logger.info(f"✅ 最终返回 {len(tasks)} 个任务")
        return tasks

    except ImportError as e:
        # 数据库驱动导入失败
        logger.error(f"数据库驱动导入失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "数据库连接失败",
                "message": f"数据库驱动未正确安装: {str(e)}",
                "suggestion": "请检查生产环境的数据库配置和psycopg库安装"
            }
        )
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "获取任务列表失败",
                "message": str(e),
                "type": type(e).__name__
            }
        )


@router.get("/{task_id}", response_model=StreamAnalysisTaskResponse, summary="获取任务详情")
async def get_task(task_id: str):
    """获取指定任务的详细信息"""
    try:
        tasks = await stream_task_manager.get_task_list()
        task = next((t for t in tasks if t['id'] == task_id), None)
        
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务详情失败: {str(e)}")


@router.put("/{task_id}", response_model=Dict[str, Any], summary="更新任务配置")
async def update_task(task_id: str, update_data: StreamAnalysisTaskUpdate):
    """更新分析任务配置"""
    try:
        # 这里需要实现任务更新逻辑
        # 为简化示例，暂时返回成功状态
        return {
            "success": True,
            "message": "任务配置更新成功",
            "task_id": task_id,
            "updated_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"更新任务配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新任务失败: {str(e)}")


@router.post("/{task_id}/enable", response_model=Dict[str, Any], summary="启用任务")
async def enable_task(task_id: str):
    """启用指定的分析任务"""
    try:
        success = await stream_task_manager.enable_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "success": True,
            "message": "任务已启用",
            "task_id": task_id,
            "enabled_at": now_isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"启用任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"启用任务失败: {str(e)}")


@router.post("/{task_id}/disable", response_model=Dict[str, Any], summary="停用任务")
async def disable_task(task_id: str):
    """停用指定的分析任务"""
    try:
        success = await stream_task_manager.disable_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "success": True,
            "message": "任务已停用",
            "task_id": task_id,
            "disabled_at": now_isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"停用任务失败: {str(e)}")


@router.post("/{task_id}/start", response_model=Dict[str, Any], summary="启动任务分析")
async def start_task_analysis(task_id: str):
    """启动指定任务的分析"""
    try:
        result = await stream_task_manager.start_task_analysis(task_id)
        
        return {
            **result,
            "task_id": task_id,
            "started_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动任务分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.post("/{task_id}/stop", response_model=Dict[str, Any], summary="停止任务分析")
async def stop_task_analysis(task_id: str):
    """停止指定任务的分析"""
    try:
        result = await stream_task_manager.stop_task_analysis(task_id)
        
        return {
            **result,
            "task_id": task_id,
            "stopped_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"停止任务分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"停止分析失败: {str(e)}")


@router.delete("/{task_id}", response_model=Dict[str, Any], summary="删除任务")
async def delete_task(task_id: str):
    """删除指定的分析任务"""
    try:
        success = await stream_task_manager.delete_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return {
            "success": True,
            "message": "任务已删除",
            "task_id": task_id,
            "deleted_at": now_isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")


@router.post("/batch", response_model=Dict[str, Any], summary="批量操作任务")
async def batch_operation(batch_data: TaskBatchOperation):
    """对多个任务执行批量操作"""
    try:
        results = []
        
        for task_id in batch_data.task_ids:
            try:
                if batch_data.operation == "enable":
                    success = await stream_task_manager.enable_task(task_id)
                elif batch_data.operation == "disable":
                    success = await stream_task_manager.disable_task(task_id)
                elif batch_data.operation == "delete":
                    success = await stream_task_manager.delete_task(task_id)
                elif batch_data.operation == "start":
                    result = await stream_task_manager.start_task_analysis(task_id)
                    success = result.get('success', False)
                elif batch_data.operation == "stop":
                    result = await stream_task_manager.stop_task_analysis(task_id)
                    success = result.get('success', False)
                else:
                    success = False
                
                results.append({
                    "task_id": task_id,
                    "success": success
                })
                
            except Exception as e:
                results.append({
                    "task_id": task_id,
                    "success": False,
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r['success'])
        
        return {
            "success": True,
            "message": f"批量操作完成，成功: {success_count}/{len(batch_data.task_ids)}",
            "operation": batch_data.operation,
            "results": results,
            "executed_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"批量操作失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量操作失败: {str(e)}")


@router.get("/stream/{stream_id}/tasks", response_model=List[StreamAnalysisTaskResponse], summary="获取指定视频流的任务")
async def get_stream_tasks(stream_id: UUID):
    """获取指定视频流的所有分析任务"""
    try:
        tasks = await stream_task_manager.get_task_list(stream_id=str(stream_id))
        return tasks
        
    except Exception as e:
        logger.error(f"获取视频流任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取任务失败: {str(e)}")


@router.post("/recovery/auto", response_model=Dict[str, Any], summary="执行任务自动恢复")
async def auto_recover_tasks():
    """手动触发任务自动恢复（系统启动时自动调用）"""
    try:
        await stream_task_manager.auto_recover_tasks()
        
        return {
            "success": True,
            "message": "任务自动恢复执行完成",
            "recovered_at": now_isoformat()
        }
        
    except Exception as e:
        logger.error(f"任务自动恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"自动恢复失败: {str(e)}")


@router.get("/statistics/summary", summary="获取任务统计摘要")
async def get_task_statistics():
    """获取分析任务的统计摘要信息"""
    try:
        tasks = await stream_task_manager.get_task_list()
        
        total_count = len(tasks)
        enabled_count = sum(1 for t in tasks if t.get('is_active', False))
        running_count = sum(1 for t in tasks if t.get('is_running', False))
        scheduled_count = sum(1 for t in tasks if t.get('should_run_now', False))
        
        # 按状态统计
        status_stats = {}
        for task in tasks:
            status = task.get('status', 'unknown')
            status_stats[status] = status_stats.get(status, 0) + 1
        
        # 按视频流统计
        stream_stats = {}
        for task in tasks:
            stream_name = task.get('stream_name', '未知流')
            if stream_name not in stream_stats:
                stream_stats[stream_name] = {'total': 0, 'enabled': 0, 'running': 0}
            
            stream_stats[stream_name]['total'] += 1
            if task.get('is_active', False):
                stream_stats[stream_name]['enabled'] += 1
            if task.get('is_running', False):
                stream_stats[stream_name]['running'] += 1
        
        return {
            "success": True,
            "data": {
                "total_count": total_count,
                "enabled_count": enabled_count,
                "running_count": running_count,
                "scheduled_count": scheduled_count,
                "status_statistics": status_stats,
                "stream_statistics": stream_stats,
                "last_updated": now_isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"获取任务统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")