"""
统一视频管理API路由
整合了视频文件上传、管理、播放、分析等完整功能
合并自原 video.py、videos.py、video_files.py 模块
"""

import logging
import uuid
import base64
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends, File, UploadFile, Form
from fastapi.responses import RedirectResponse, FileResponse
from pydantic import BaseModel

from services.video_file_service import VideoFileService
from storage.services.minio_client import MinIOClient
from models.video_file import (
    VideoFileCreate, VideoFileUpdate, VideoFileResponse, 
    VideoAnalysisTemplateCreate, VideoStatusEnum
)
from config.settings import PathConfig
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-files", tags=["视频文件管理"])


class VideoSearchParams(BaseModel):
    """视频搜索参数"""
    search_name: Optional[str] = None
    status: Optional[VideoStatusEnum] = None  
    tags: Optional[List[str]] = None
    limit: int = 20
    offset: int = 0


@router.get("/", response_model=List[VideoFileResponse], summary="搜索视频列表")
async def get_videos(
    search_name: Optional[str] = Query(None, description="按名称搜索"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    tags: Optional[str] = Query(None, description="按标签筛选,逗号分隔"),
    limit: int = Query(20, ge=1, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取视频列表，支持搜索和筛选"""
    try:
        # 处理标签参数
        tag_list = None
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",")]
        
        videos = await VideoFileService.get_videos_with_search(
            search_name=search_name,
            status=status, 
            tags=tag_list,
            limit=limit,
            offset=offset
        )
        
        return videos
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频列表失败: {str(e)}")


@router.get("/{video_id}", response_model=VideoFileResponse, summary="获取视频详情")
async def get_video(video_id: str):
    """根据ID获取视频详细信息"""
    try:
        video = await VideoFileService.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频信息失败: {str(e)}")


@router.post("/upload", response_model=VideoFileResponse, summary="上传视频文件")
async def upload_video(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None)
):
    """上传视频文件到MinIO存储"""
    try:
        # 验证文件类型
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv')):
            raise HTTPException(status_code=400, detail="不支持的视频格式")
        
        # 读取文件内容
        file_content = await file.read()
        file_size = len(file_content)
        
        # 验证文件大小 (500MB限制)
        max_size = 500 * 1024 * 1024  # 500MB
        if file_size > max_size:
            raise HTTPException(status_code=400, detail="文件大小超过限制（最大500MB）")
        
        # 生成唯一的对象键
        file_extension = file.filename.split('.')[-1].lower()
        timestamp = now().strftime("%Y%m%d_%H%M%S")
        object_key = f"uploads/{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
        
        # 初始化MinIO客户端并上传文件
        minio_client = MinIOClient()
        
        # 设置内容类型
        content_type_map = {
            'mp4': 'video/mp4',
            'avi': 'video/x-msvideo', 
            'mov': 'video/quicktime',
            'wmv': 'video/x-ms-wmv',
            'flv': 'video/x-flv'
        }
        content_type = content_type_map.get(file_extension, 'video/mp4')
        
        # 上传到MinIO（元数据只能包含ASCII字符）
        # 将中文文件名进行Base64编码以符合ASCII要求
        original_filename_encoded = base64.b64encode(file.filename.encode('utf-8')).decode('ascii')
        
        minio_file_info = await minio_client.upload_file(
            bucket_name="videos",
            object_key=object_key,
            file_content=file_content,
            content_type=content_type,
            metadata={
                "original_filename_b64": original_filename_encoded,  # Base64编码的原始文件名
                "uploaded_by": "system",  # 后续可以从用户认证中获取
                "upload_time": now_isoformat(),
                "file_size": str(file_size),
                "content_type": content_type
            }
        )
        
        # 生成MinIO访问路径
        minio_path = f"videos/{object_key}"
        
        # 创建数据库记录
        video_data = VideoFileCreate(
            name=name,
            original_filename=file.filename,
            file_path=minio_path,  # 存储MinIO路径而不是本地路径
            description=description,
            tags=tags.split(',') if tags else [],
            file_size=file_size,
            format=file_extension.upper(),
            status=VideoStatusEnum.READY  # 上传成功后立即设为READY状态，可以播放
        )
        
        db_video = await VideoFileService.create_video(video_data)
        
        logger.info(f"视频文件已上传到MinIO并入库: {minio_path}")
        return db_video
        
    except Exception as e:
        logger.error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/", response_model=VideoFileResponse, summary="创建视频记录")
async def create_video(video_data: VideoFileCreate):
    """创建新的视频文件记录"""
    try:
        return await VideoFileService.create_video(video_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建视频记录失败: {str(e)}")


@router.put("/{video_id}", response_model=VideoFileResponse, summary="更新视频信息")
async def update_video(video_id: str, update_data: VideoFileUpdate):
    """更新视频信息"""
    try:
        video = await VideoFileService.update_video(video_id, update_data)
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        return video
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新视频信息失败: {str(e)}")


@router.delete("/{video_id}", summary="删除视频")
async def delete_video(video_id: str):
    """删除视频文件（软删除）"""
    try:
        success = await VideoFileService.delete_video(video_id)
        if not success:
            raise HTTPException(status_code=404, detail="视频不存在")
        return {"message": "视频删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除视频失败: {str(e)}")


@router.get("/statistics/summary", summary="获取视频统计信息")
async def get_video_statistics():
    """获取视频管理统计信息"""
    try:
        return await VideoFileService.get_video_statistics()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.post("/{video_id}/analysis/configure", summary="配置视频分析算法")
async def configure_analysis(video_id: str, config_data: VideoAnalysisTemplateCreate):
    """
    为视频配置AI分析算法模板（支持复合检测）

    Args:
        video_id: 视频ID
        config_data: 配置数据，包含template_ids和detection_type_codes

    Example:
        {
            "video_id": "xxx",
            "template_ids": ["model-1"],
            "detection_type_codes": ["safety_helmet", "smoking", "phone_usage"]
        }
    """
    try:
        success = await VideoFileService.configure_analysis_templates(
            video_id,
            config_data.template_ids,
            detection_type_codes=config_data.detection_type_codes or []
        )

        if not success:
            raise HTTPException(status_code=400, detail="配置分析算法失败")

        detection_count = len(config_data.detection_type_codes or [])
        message = f"分析算法配置成功: {len(config_data.template_ids)}个AI模型"
        if detection_count > 0:
            message += f", {detection_count}个检测类型"

        return {
            "message": message,
            "template_count": len(config_data.template_ids),
            "detection_type_count": detection_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"配置分析算法失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置分析算法失败: {str(e)}")


@router.get("/{video_id}/analysis/templates", summary="获取视频分析模板")
async def get_analysis_templates(video_id: str):
    """获取视频配置的分析模板"""
    try:
        templates = await VideoFileService.get_analysis_templates(video_id)
        return {"templates": templates}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分析模板失败: {str(e)}")


@router.get("/detection-types/templates", summary="获取所有检测类型模板")
async def get_detection_type_templates():
    """
    获取所有可用的检测类型模板（用于复合检测配置）

    返回detection_type_templates表中的所有启用的模板，
    用于前端展示和选择检测类型。
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        templates = await video_analysis_template_service.get_detection_type_templates()

        return {
            "templates": templates,
            "total": len(templates),
            "message": "成功获取检测类型模板列表"
        }

    except Exception as e:
        logger.error(f"获取检测类型模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取检测类型模板失败: {str(e)}")


@router.post("/detection-types/batch-import", summary="批量导入检测类型模板")
async def batch_import_detection_types(templates: List[dict]):
    """
    批量导入检测类型模板

    Args:
        templates: 模板列表，每个模板包含type_code, display_name, category等字段
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        if not templates:
            raise HTTPException(status_code=400, detail="模板列表不能为空")

        result = await video_analysis_template_service.batch_import_detection_types(templates)

        return {
            "result": result,
            "message": f"批量导入完成: 成功{result['success_count']}个，失败{result['fail_count']}个"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量导入检测类型模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量导入失败: {str(e)}")


@router.post("/detection-types", summary="创建检测类型模板")
async def create_detection_type_template(template_data: dict):
    """
    创建新的检测类型模板

    Args:
        template_data: 模板数据，包含:
            - type_code: 类型编码(必填，唯一)
            - display_name: 显示名称(必填)
            - category: 类别(必填): safety, behavior, environment, security
            - severity: 严重程度: low, medium, high
            - prompt_template: 提示词模板
            - json_field_name: JSON字段名
            - description: 描述
            - example_scenarios: 示例场景
            - sort_order: 排序顺序
            - enabled: 是否启用
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        # 验证必填字段
        required_fields = ['type_code', 'display_name', 'category']
        for field in required_fields:
            if field not in template_data:
                raise HTTPException(status_code=400, detail=f"缺少必填字段: {field}")

        template = await video_analysis_template_service.create_detection_type_template(template_data)

        if not template:
            raise HTTPException(status_code=500, detail="创建检测类型模板失败")

        return {
            "template": template,
            "message": "成功创建检测类型模板"
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建检测类型模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建检测类型模板失败: {str(e)}")


@router.put("/detection-types/{type_code}", summary="更新检测类型模板")
async def update_detection_type_template(type_code: str, template_data: dict):
    """
    更新检测类型模板

    Args:
        type_code: 要更新的模板编码
        template_data: 更新的数据（支持部分更新）
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        template = await video_analysis_template_service.update_detection_type_template(type_code, template_data)

        if not template:
            raise HTTPException(status_code=404, detail=f"未找到检测类型: {type_code}")

        return {
            "template": template,
            "message": "成功更新检测类型模板"
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新检测类型模板失败 {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"更新检测类型模板失败: {str(e)}")


@router.delete("/detection-types/{type_code}", summary="删除检测类型模板")
async def delete_detection_type_template(type_code: str):
    """
    删除检测类型模板（软删除）

    Args:
        type_code: 要删除的模板编码
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        success = await video_analysis_template_service.delete_detection_type_template(type_code)

        if not success:
            raise HTTPException(status_code=404, detail=f"未找到检测类型: {type_code}")

        return {
            "message": f"成功删除检测类型模板: {type_code}"
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除检测类型模板失败 {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"删除检测类型模板失败: {str(e)}")


@router.get("/detection-types/{type_code}", summary="获取单个检测类型模板")
async def get_detection_type_by_code(type_code: str):
    """
    根据type_code获取单个检测类型模板详情

    Args:
        type_code: 检测类型编码（如safety_helmet, smoking等）
    """
    try:
        from services.video_analysis_template_service import video_analysis_template_service

        template = await video_analysis_template_service.get_detection_type_by_code(type_code)

        if not template:
            raise HTTPException(status_code=404, detail=f"未找到检测类型: {type_code}")

        return {
            "template": template,
            "message": "成功获取检测类型模板"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取检测类型模板失败 {type_code}: {e}")
        raise HTTPException(status_code=500, detail=f"获取检测类型模板失败: {str(e)}")


@router.post("/{video_id}/analysis/start", summary="启动视频分析")
async def start_analysis(video_id: str):
    """启动视频分析任务"""
    try:
        from services.video_analysis_service import video_analysis_service
        
        # 启动真实的分析任务
        result = await video_analysis_service.start_analysis(video_id)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动分析失败: {str(e)}")


@router.get("/{video_id}/analysis/status", summary="获取视频分析状态")
async def get_analysis_status(video_id: str):
    """获取视频分析任务状态"""
    try:
        from services.video_analysis_service import video_analysis_service
        
        # 首先查找正在运行的任务
        for task_id, task in video_analysis_service.running_tasks.items():
            if task.video_id == video_id:
                return task.to_dict()
        
        # 如果没有正在运行的任务，从数据库获取视频状态和进度
        video = await VideoFileService.get_video_by_id(video_id)
        if not video:
            return {"message": "视频不存在", "video_id": video_id}
        
        # 返回视频的分析状态
        return {
            "video_id": video_id,
            "status": video.status.value if hasattr(video.status, 'value') else str(video.status),
            "progress": (video.analysis_progress or 0) / 100.0,  # 转换为0-1的进度值
            "analysis_progress": video.analysis_progress or 0,    # 百分比进度
            "analyzed_at": video.analyzed_at.isoformat() if video.analyzed_at else None,
            "total_alerts": video.total_alerts or 0,
            "last_alert_at": video.last_alert_at.isoformat() if video.last_alert_at else None,
            "message": "从数据库获取的状态"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取分析状态失败: {str(e)}")


@router.post("/{video_id}/analysis/stop", summary="停止视频分析")
async def stop_analysis(video_id: str):
    """停止视频分析任务"""
    try:
        from services.video_analysis_service import video_analysis_service
        
        # 查找并停止该视频的分析任务
        for task_id, task in video_analysis_service.running_tasks.items():
            if task.video_id == video_id and task.status == "running":
                success = await video_analysis_service.stop_task(task_id)
                if success:
                    return {"message": "分析任务已停止", "task_id": task_id, "video_id": video_id}
        
        return {"message": "未找到正在运行的分析任务", "video_id": video_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止分析失败: {str(e)}")


@router.get("/files/{filename}", summary="获取视频文件")
@router.head("/files/{filename}")
async def get_video_file(filename: str):
    """获取视频文件 - 通过后端代理流式返回"""
    try:
        # 首先检查是否是旧的本地文件（向后兼容）
        local_file_path = PathConfig.UPLOAD_DIR / filename
        if local_file_path.exists():
            logger.warning(f"访问旧版本本地文件: {filename}")
            return FileResponse(
                path=str(local_file_path),
                filename=filename,
                media_type="video/mp4"
            )
        
        # 尝试通过原始文件名查找数据库中的文件记录
        from services.video_file_service import VideoFileService
        video_by_filename = await VideoFileService.get_video_by_original_filename(filename)
        
        # 尝试从MinIO获取文件
        minio_client = MinIOClient()
        bucket_name = "videos"
        
        # 构造可能的对象键路径
        possible_keys = []
        
        # 如果从数据库找到了文件，使用数据库中的路径
        if video_by_filename and video_by_filename.file_path.startswith("videos/"):
            actual_key = video_by_filename.file_path[7:]  # 移除 "videos/" 前缀
            possible_keys.append(actual_key)
            logger.info(f"从数据库找到文件: {filename} -> {actual_key}")
        
        # 添加其他可能的路径
        possible_keys.extend([
            f"uploads/{filename}",  # 新版本路径
            filename,  # 直接文件名
        ])
        
        from fastapi.responses import StreamingResponse
        
        for object_key in possible_keys:
            try:
                # 直接从MinIO获取文件并流式返回
                response = minio_client.client.get_object(bucket_name, object_key)
                
                def iterfile():
                    try:
                        while True:
                            chunk = response.read(8192)
                            if not chunk:
                                break
                            yield chunk
                    finally:
                        response.close()
                        response.release_conn()
                
                logger.info(f"通过后端代理获取文件: {bucket_name}/{object_key}")
                return StreamingResponse(
                    iterfile(), 
                    media_type="video/mp4",
                    headers={
                        "Accept-Ranges": "bytes",
                        "Cache-Control": "no-cache",
                    }
                )
                
            except Exception as e:
                # 如果这个键不存在，尝试下一个
                logger.debug(f"尝试获取 {object_key} 失败: {e}")
                continue
        
        # 如果都找不到，返回404
        logger.warning(f"文件不存在: {filename}")
        raise HTTPException(status_code=404, detail="文件不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取文件失败: {str(e)}")


@router.get("/stream/{video_id}", summary="流式播放视频")
async def stream_video_by_id(video_id: str):
    """通过视频ID流式播放视频"""
    try:
        # 从数据库获取视频信息
        video = await VideoFileService.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="视频不存在")
        
        # 解析MinIO路径
        if video.file_path.startswith("videos/"):
            # 新版本MinIO路径格式: videos/uploads/xxx.mp4
            bucket_name = "videos"
            object_key = video.file_path[7:]  # 移除 "videos/" 前缀
        else:
            # 旧版本本地路径，重定向到files接口
            return RedirectResponse(url=f"/api/video-files/files/{video.original_filename}")
        
        # 通过后端代理文件流，而不是使用预签名URL
        try:
            minio_client = MinIOClient()
            
            # 直接从MinIO获取文件并流式返回
            from fastapi.responses import StreamingResponse
            import httpx
            
            # 获取文件对象
            response = minio_client.client.get_object(bucket_name, object_key)
            
            def iterfile():
                try:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    response.close()
                    response.release_conn()
            
            logger.info(f"通过后端代理流式播放视频: {video_id} -> {bucket_name}/{object_key}")
            return StreamingResponse(
                iterfile(), 
                media_type="video/mp4",
                headers={
                    "Accept-Ranges": "bytes",
                    "Cache-Control": "no-cache",
                }
            )
        except Exception as e:
            logger.error(f"从MinIO获取视频文件失败: {e}")
            raise HTTPException(status_code=404, detail="视频文件不存在")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"流式播放视频失败: {e}")
        raise HTTPException(status_code=500, detail=f"流式播放失败: {str(e)}")