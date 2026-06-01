"""
重构后的视频分析服务
使用模块化设计，依赖注入各个专门的服务组件
"""

import asyncio
import logging
import cv2
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path

from models.video_file import VideoStatusEnum
from services.video_file_service import VideoFileService
from services.video_analysis_task import VideoAnalysisTask
from services.frame_analyzer import FrameAnalyzer
from services.analysis_result_processor import AnalysisResultProcessor
from services.storage import storage_service
from services.video_analysis_template_service import video_analysis_template_service
from services.ai_analysis_log_service import ai_analysis_log_service
from services.helpers.video_frame_extractor import (
    extract_violation_from_ai_response as _extract_violation_helper,
    convert_violations_to_results as _convert_violations_helper,
)
from config.settings import PathConfig, VideoConfig
from utils.timezone_utils import now

logger = logging.getLogger(__name__)


class VideoAnalysisService:
    """重构后的视频分析服务 - 使用依赖注入和模块化设计"""
    
    def __init__(self):
        # 依赖注入各个专门服务
        self.frame_analyzer = FrameAnalyzer()
        self.result_processor = AnalysisResultProcessor()
        
        # 任务管理
        self.running_tasks: Dict[str, VideoAnalysisTask] = {}
        self.task_queue = asyncio.Queue()
        self.worker_task = None
        self._start_worker()
    
    def _start_worker(self):
        """启动后台任务处理器"""
        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(self._process_tasks())
    
    async def start_analysis(self, video_id: str, template_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """启动视频分析"""
        try:
            # 获取视频信息
            video = await VideoFileService.get_video_by_id(video_id)
            if not video:
                raise ValueError("视频不存在")
            
            # 移除状态校验，允许任何状态的视频进行分析
            
            # 从数据库获取该视频配置的分析算法
            if not template_ids:
                templates = await video_analysis_template_service.get_video_analysis_templates(video_id)
                if not templates:
                    # 如果没有配置模板，提示用户先配置
                    raise ValueError("请先配置视频分析算法，然后再启动分析")
                template_ids = [t.get('template_id') or t['id'] for t in templates if t.get('enabled', True)]

            if not template_ids:
                raise ValueError("没有启用的分析算法配置")
            
            # 创建分析任务
            task = VideoAnalysisTask(video_id, template_ids)
            self.running_tasks[task.id] = task
            
            # 更新视频状态
            await VideoFileService.update_video_status(video_id, VideoStatusEnum.ANALYZING)
            
            # 加入任务队列
            await self.task_queue.put(task)
            
            logger.info(f"视频分析任务已创建: {task.id}, 视频: {video_id}")
            
            return {
                'task_id': task.id,
                'video_id': video_id,
                'template_count': len(template_ids),
                'status': 'queued'
            }
            
        except Exception as e:
            logger.error(f"启动视频分析失败: {e}")
            raise
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.running_tasks.get(task_id)
        return task.to_dict() if task else None
    
    async def stop_task(self, task_id: str) -> bool:
        """停止分析任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = "cancelled"
            task.error_message = "用户取消"
            task.completed_at = now()
            return True
        return False
    
    async def _process_tasks(self):
        """后台任务处理器"""
        logger.info("视频分析任务处理器已启动")
        
        while True:
            try:
                task = await self.task_queue.get()
                if task.status != "cancelled":
                    await self._execute_task(task)
                self.task_queue.task_done()
                
            except Exception as e:
                logger.error(f"任务处理器异常: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: VideoAnalysisTask):
        """执行单个分析任务"""
        try:
            task.status = "running"
            task.started_at = now()
            
            # 重置分析进度为0
            await self._sync_progress_to_db(task.video_id, 0)
            
            # 设置当前任务和视频ID用于日志记录
            self.current_task_id = task.id
            self.current_video_id = task.video_id
            
            logger.info(f"开始执行任务: {task.id}")
            
            # 获取视频文件
            video = await VideoFileService.get_video_by_id(task.video_id)
            if not video or not video.file_path:
                raise ValueError("无法获取视频文件路径")
            
            # 获取分析算法模板配置（从ai_model_configs表）
            vat_templates = await video_analysis_template_service.get_video_analysis_templates(task.video_id)
            # 只使用启用的模板
            vat_templates = [t for t in vat_templates if t.get('enabled', True)]

            if not vat_templates:
                raise ValueError("没有有效的分析算法")

            # 从ai_model_configs表查询完整的算法配置（支持复合检测）
            templates = []
            from database.connection import DatabaseManager
            from sqlalchemy import text

            async with DatabaseManager.get_session() as db:
                for vat in vat_templates:
                    # 获取template_id（ai_model_configs.id）
                    template_id = vat.get('template_id') or vat.get('id')

                    # 从ai_model_configs表查询算法详细配置
                    query = text("""
                        SELECT
                            id, name, description, provider, model_name,
                            system_prompt, user_prompt, temperature, top_p, max_tokens,
                            confidence_threshold, tags, detection_capabilities
                        FROM ai_model_configs
                        WHERE id = :template_id
                    """)
                    result = await db.execute(query, {'template_id': template_id})
                    row = result.fetchone()

                    if row:
                        # 获取检测能力列表（用于复合检测）
                        detection_capabilities = row[12] if row[12] else []

                        # 提取第一个detection_type_code（用于向后兼容）
                        detection_type_code = detection_capabilities[0] if detection_capabilities else None

                        # 构建完整的模板配置
                        template = {
                            'id': str(row[0]),
                            'name': row[1],
                            'description': row[2],
                            'category': vat.get('category', 'analysis'),
                            'priority': vat.get('priority', 1),
                            'confidence_threshold': vat.get('confidence_threshold', row[10]),

                            # AI模型配置
                            'provider': row[3],
                            'model_name': row[4],
                            'system_prompt': row[5],
                            'user_prompt': row[6],
                            'temperature': float(row[7]) if row[7] else 0.7,
                            'top_p': float(row[8]) if row[8] else 0.9,
                            'max_tokens': row[9] if row[9] else 1000,

                            # 复合检测配置
                            'detection_capabilities': detection_capabilities,
                            'detection_type_code': detection_type_code,

                            # 用于向后兼容的字段
                            'prompt_content': row[6] if row[6] else row[5]
                        }
                        templates.append(template)

                        if detection_capabilities:
                            logger.info(f"✅ 加载算法配置: {template['name']}, 检测能力: {detection_capabilities}")
                        else:
                            logger.warning(f"⚠️  算法配置缺少检测能力: {template['name']} (ID: {template_id})")
                    else:
                        logger.error(f"❌ 未找到算法配置: template_id={template_id}")

            if not templates:
                raise ValueError("未能加载任何有效的算法配置，请检查ai_model_configs表")
            
            # 分析视频
            results = await self._analyze_video_frames(video.file_path, templates, task)
            
            # 处理分析结果
            task.results = results
            await self.result_processor.process_analysis_results(task, results)

            # 更新任务状态
            task.status = "completed"
            task.completed_at = now()

            # 更新ES中的任务状态（修复状态不同步问题）
            await self._update_task_status_in_es(task)

            # 分析完成，设置进度为100%
            await self._sync_progress_to_db(task.video_id, 100)

            # 更新视频状态
            await VideoFileService.update_video_status(task.video_id, VideoStatusEnum.COMPLETED)

            logger.info(f"任务执行完成: {task.id}, 分析了 {len(results)} 帧")
            
        except Exception as e:
            logger.error(f"任务执行失败 {task.id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = now()

            # 更新ES中的任务状态（失败状态）
            try:
                await self._update_task_status_in_es(task)
            except Exception as es_error:
                logger.error(f"更新ES任务状态失败: {es_error}")

            # 更新视频状态为失败
            try:
                await VideoFileService.update_video_status(task.video_id, VideoStatusEnum.ERROR)
            except Exception as update_error:
                logger.error(f"更新视频状态失败: {update_error}")
    
    async def _analyze_video_frames(self, video_path: str, templates: List[Any],
                                  task: VideoAnalysisTask) -> List[Dict[str, Any]]:
        """分析视频帧"""
        try:
            results = []
            local_video_path = None
            failed_frames_count = 0  # 失败帧计数
            total_analyzed_frames = 0  # 总分析帧数
            FAILURE_RATE_THRESHOLD = 0.8  # 失败率阈值80%
            
            # 判断是否为MinIO路径，如果是则先下载到本地
            if video_path.startswith(('videos/', 'multi-videos/')):
                logger.info(f"从MinIO下载视频文件: {video_path}")
                try:
                    # 确定bucket和object_key
                    if video_path.startswith('videos/'):
                        bucket_name = 'videos'
                        object_key = video_path[7:]  # 移除 'videos/' 前缀
                    else:
                        bucket_name = 'multi-videos'
                        object_key = video_path[13:]  # 移除 'multi-videos/' 前缀
                    
                    # 从MinIO下载文件
                    video_content = await storage_service.minio_client.download_file(bucket_name, object_key)
                    
                    # 保存到临时文件
                    temp_dir = Path(PathConfig.TEMP_DIR) / f"analysis_{task.id}"
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    local_video_path = temp_dir / f"video_{task.id}.mp4"
                    
                    with open(local_video_path, 'wb') as f:
                        f.write(video_content)
                    
                    video_path = str(local_video_path)
                    logger.info(f"视频文件已下载到本地: {video_path}")
                    
                except Exception as download_error:
                    logger.error(f"从MinIO下载视频失败: {download_error}")
                    # 尝试使用预签名URL
                    try:
                        presigned_url = await storage_service.minio_client.get_presigned_url(bucket_name, object_key)
                        video_path = presigned_url
                        logger.info(f"使用预签名URL访问视频: {presigned_url}")
                    except Exception as url_error:
                        logger.error(f"生成预签名URL失败: {url_error}")
                        raise ValueError(f"无法访问MinIO视频文件: {video_path}")
            
            # 打开视频文件
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频属性
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            logger.info(f"视频信息: {total_frames} 帧, {fps} FPS")
            
            # 计算采样间隔（每5秒分析一帧）
            frame_interval = max(1, int(fps * VideoConfig.FRAME_SAMPLE_INTERVAL))
            
            # 创建临时目录
            temp_dir = Path(PathConfig.TEMP_DIR) / f"analysis_{task.id}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            frame_index = 0
            processed_frames = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # 跳帧采样
                if frame_index % frame_interval == 0:
                    timestamp = frame_index / fps
                    
                    # 保存帧图片
                    frame_filename = f"frame_{frame_index:06d}.jpg"
                    frame_path = temp_dir / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    
                    # 上传到MinIO
                    minio_url = await storage_service.upload_frame_image(
                        str(frame_path), task.id, frame_index
                    )
                    
                    # 分析单帧 (使用本地路径进行AI分析，保存MinIO URL到结果中)
                    frame_result = await self._analyze_single_frame(
                        frame_index, timestamp, templates, str(frame_path), minio_url
                    )

                    if frame_result:
                        results.extend(frame_result)
                        # 统计失败的帧
                        for result in frame_result:
                            total_analyzed_frames += 1
                            if result.get('error') or result.get('confidence', 1.0) == 0.0:
                                failed_frames_count += 1

                    processed_frames += 1

                    # 检查失败率(处理至少3帧后开始检查)
                    if total_analyzed_frames >= 3:
                        failure_rate = failed_frames_count / total_analyzed_frames
                        if failure_rate >= FAILURE_RATE_THRESHOLD:
                            error_msg = f"AI分析失败率过高 ({failure_rate*100:.1f}%), 已分析{total_analyzed_frames}帧, 失败{failed_frames_count}帧"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                    
                    # 更新进度
                    task.progress = min(frame_index / total_frames, 1.0)
                    
                    # 同步进度到数据库（每5%更新一次）
                    progress_percentage = int(task.progress * 100)
                    if progress_percentage % 5 == 0 and progress_percentage != getattr(task, '_last_synced_progress', -1):
                        await self._sync_progress_to_db(task.video_id, progress_percentage)
                        task._last_synced_progress = progress_percentage
                    
                    # 检查是否需要取消
                    if task.status == "cancelled":
                        logger.info(f"任务被取消: {task.id}")
                        break
                
                frame_index += 1
            
            cap.release()
            
            # 清理临时文件
            try:
                import shutil
                # 清理帧图片临时目录
                shutil.rmtree(temp_dir)
                
                # 清理下载的视频文件
                if local_video_path and local_video_path.exists():
                    local_video_path.unlink()
                    logger.debug(f"已清理下载的视频文件: {local_video_path}")
                    
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")

            # 最终检查失败率
            if total_analyzed_frames > 0:
                final_failure_rate = failed_frames_count / total_analyzed_frames
                logger.info(f"视频分析完成: 处理了 {processed_frames} 帧，生成了 {len(results)} 个结果")
                logger.info(f"分析统计: 总帧数={total_analyzed_frames}, 失败={failed_frames_count}, 失败率={final_failure_rate*100:.1f}%")

                # 如果最终失败率过高,抛出异常
                if final_failure_rate >= FAILURE_RATE_THRESHOLD:
                    raise ValueError(f"视频分析失败率过高({final_failure_rate*100:.1f}%), 请检查AI模型配置")
            else:
                logger.warning("未成功分析任何帧")

            return results
            
        except Exception as e:
            logger.error(f"分析视频帧失败: {e}")
            raise
    
    async def _analyze_via_inference(
        self,
        frame_index: int,
        timestamp: float,
        templates: List[Dict[str, Any]],
        image_path: str,
        minio_url: Optional[str],
    ) -> Optional[List[Dict[str, Any]]]:
        """
        调用 A100 推理服务完成单帧检测

        返回 None 表示未产生结果（调用方应降级）；
        抛 InferenceUnavailable/InferenceHTTPError 由调用方捕获降级。
        """
        from services.inference_client import inference_client
        import time

        # 推算帧图片在 MinIO 的 key（与 storage.upload_frame_image 约定一致）
        minio_key = f"analysis/{getattr(self, 'current_task_id', 'unknown')}/frame_{frame_index:06d}.jpg"
        request_id = f"{getattr(self, 'current_task_id', 'notask')}-f{frame_index}"

        # 多模板情况下：A100 的 /v1/analyze 是单模板单次调用；
        # 这里为每个模板并发调一次，汇总为 results 列表
        results: List[Dict[str, Any]] = []
        for template in templates:
            violations_hint: List[str] = []
            # 从 detection_capabilities 取违规类型中文名（已是中文 code 或名称）
            caps = template.get("detection_capabilities") or []
            if isinstance(caps, list):
                violations_hint = [str(c) for c in caps if c]

            start = time.time()
            inference_result = await inference_client.analyze(
                image_minio_key=minio_key,
                template=template,
                violations_hint=violations_hint,
                request_id=request_id,
            )
            elapsed_ms = int((time.time() - start) * 1000)

            vlm = inference_result.vlm_result
            has_alert = bool(vlm.has_violation)
            # 置信度：取最大 detection confidence 或 VLM 默认 0.85
            if inference_result.detection_objects:
                conf = max(obj.confidence for obj in inference_result.detection_objects)
            else:
                conf = 0.85 if has_alert else 0.0

            detection_objects = [obj.model_dump() for obj in inference_result.detection_objects]

            results.append({
                "frame_index": frame_index,
                "timestamp": timestamp,
                "template_id": template.get("id"),
                "template_name": template.get("name"),
                "category": template.get("category", "analysis"),
                "image_url": minio_url or image_path,
                "has_alert": has_alert,
                "ai_response": vlm.raw_text or vlm.scene_description or "",
                "description": vlm.scene_description,
                "confidence": float(conf),
                "detection_objects": detection_objects,
                "image_size": inference_result.image_size,
                "inference_request_id": inference_result.request_id,
                "inference_latency_ms": inference_result.total_latency_ms,
                "source": "vistrat_a100",
            })

            logger.info(
                f"[{request_id}] ✅ A100 帧{frame_index} 模板={template.get('name')} "
                f"violation={has_alert} bbox={len(detection_objects)} "
                f"a100_ms={inference_result.total_latency_ms} client_ms={elapsed_ms}"
            )

        return results if results else None

    def _convert_inference_to_annotations(
        self, result, template: Dict[str, Any]
    ) -> List[Any]:
        """
        将 InferenceResult 的 detection_objects 转为 AnnotationObject（供旧链路复用）

        注意：主路径的结果已是 dict 形式写入 ES（见 _analyze_via_inference），
        本方法只在需要 AnnotationObject 列表的旧代码里用。
        """
        from models.analysis_result import AnnotationObject, BoundingBox, AlertSeverity

        annotations: List[AnnotationObject] = []
        severity_map = {
            "critical": AlertSeverity.CRITICAL,
            "high": AlertSeverity.HIGH,
            "medium": AlertSeverity.MEDIUM,
            "low": AlertSeverity.LOW,
            "info": AlertSeverity.INFO,
        }
        for obj in result.detection_objects:
            annotations.append(AnnotationObject(
                class_name=obj.label,
                confidence=obj.confidence,
                bounding_box=BoundingBox(
                    x=float(obj.bbox.x),
                    y=float(obj.bbox.y),
                    width=float(obj.bbox.width),
                    height=float(obj.bbox.height),
                    confidence=obj.confidence,
                ),
                label=obj.label,
                is_violation=True,
                severity=severity_map.get(obj.severity, AlertSeverity.MEDIUM),
            ))
        return annotations

    async def _analyze_single_frame(self, frame_index: int, timestamp: float,
                                  templates: List[Any], image_path: str, minio_url: str = None) -> List[Dict[str, Any]]:
        """
        分析单个视频帧（复合检测版本）

        一次AI调用同时检测多种违规类型，大幅降低成本和提升速度

        优先走 Vistrat A100 推理服务（VLM+DINO 联合）；
        推理服务不可达 / 熔断时，自动降级到本地 composite_detection_service（仅 VLM 文字）。
        """
        # === A100 推理路径 ===
        from config.settings import InferenceConfig
        if InferenceConfig.ENABLED and templates:
            try:
                from services.inference_client import (
                    inference_client, InferenceUnavailable, InferenceHTTPError
                )
                a100_results = await self._analyze_via_inference(
                    frame_index=frame_index,
                    timestamp=timestamp,
                    templates=templates,
                    image_path=image_path,
                    minio_url=minio_url,
                )
                if a100_results is not None:
                    return a100_results
            except InferenceUnavailable as e:
                logger.warning(f"[帧{frame_index}] A100 不可用，降级到本地: {e}")
            except InferenceHTTPError as e:
                logger.error(f"[帧{frame_index}] A100 4xx 错误，降级到本地: {e}")
            except Exception as e:
                logger.error(f"[帧{frame_index}] A100 调用异常，降级到本地: {e}")

        # === 降级路径：原有 composite 流程 ===
        try:
            from services.composite_detection_service import get_composite_detection_service
            import time

            # 1. 获取复合检测服务实例
            composite_service = get_composite_detection_service()

            # 2. 确定使用的AI模型配置（使用第一个模板的model_config_id）
            model_config_id = None
            for template in templates:
                if template.get('id'):
                    model_config_id = template['id']
                    break

            # 如果没有找到model_config_id，获取默认配置
            if not model_config_id:
                from services.ai_config_manager import ai_config_manager
                configs = await ai_config_manager.get_all_active_configs()
                if configs:
                    # 优先使用GPT模型
                    for config_id, config in configs.items():
                        if config['provider'].lower() in ['gpt', 'openai']:
                            model_config_id = config_id
                            logger.info(f"使用GPT模型配置: {config['name']}")
                            break
                    # 如果没有GPT，使用第一个可用模型
                    if not model_config_id:
                        model_config_id = list(configs.keys())[0]
                        config = configs[model_config_id]
                        logger.info(f"使用默认模型配置: {config['name']} ({config['provider']})")
                else:
                    raise ValueError("无可用的AI模型配置")

            # 3. 记录开始时间
            start_time = time.time()

            # 4. 调用复合检测服务
            logger.info(
                f"🚀 帧{frame_index}启动复合检测: "
                f"{len(templates)}种算法, model={model_config_id}"
            )

            # 🔧 修复：始终使用本地路径，让unified_ai_client根据模型类型决定：
            #   - 本地模型（vLLM）：转换为MinIO内网URL
            #   - 公网模型（lanyi、qwen等）：下载并转base64编码
            final_image_path = image_path

            composite_result = await composite_service.analyze_frame_composite(
                image_path=final_image_path,
                template_configs=templates,
                model_config_id=model_config_id
            )

            # 5. 计算响应时间
            response_time_ms = int((time.time() - start_time) * 1000)

            # 6. 检查复合检测是否成功
            if not composite_result.get('success'):
                error_msg = composite_result.get('error', 'Unknown error')
                logger.error(f"帧{frame_index}复合检测失败: {error_msg}")

                # 记录失败日志
                for template in templates:
                    await ai_analysis_log_service.log_failed_call(
                        task_id=str(getattr(self, 'current_task_id', 'unknown')),
                        video_id=str(getattr(self, 'current_video_id', 'unknown')),
                        algorithm_id=template['id'],
                        algorithm_config_id=model_config_id,
                        model_name='unknown',
                        frame_index=frame_index,
                        frame_timestamp=str(timestamp),
                        request_data={'composite_detection': True},
                        error_message=error_msg,
                        error_code='COMPOSITE_DETECTION_ERROR',
                        response_time_ms=response_time_ms
                    )

                # 返回错误结果（为每个template创建一个错误result）
                return [{
                    'frame_index': frame_index,
                    'timestamp': timestamp,
                    'template_id': template['id'],
                    'template_name': template['name'],
                    'category': template['category'],
                    'image_url': minio_url or image_path,
                    'has_alert': False,
                    'ai_response': f"复合检测失败: {error_msg}",
                    'confidence': 0.0,
                    'error': error_msg
                } for template in templates]

            # 7. 将violations转换为results格式
            results = self._convert_violations_to_results(
                violations=composite_result['violations'],
                templates=templates,
                frame_index=frame_index,
                timestamp=timestamp,
                minio_url=minio_url or image_path,
                composite_result=composite_result
            )

            # 8. 记录成功的AI调用日志
            for result in results:
                await ai_analysis_log_service.log_success_call(
                    task_id=str(getattr(self, 'current_task_id', 'unknown')),
                    video_id=str(getattr(self, 'current_video_id', 'unknown')),
                    algorithm_id=result['template_id'],
                    algorithm_config_id=model_config_id,
                    model_name=composite_result.get('model_used', 'unknown'),
                    frame_index=frame_index,
                    frame_timestamp=str(timestamp),
                    request_data={
                        'composite_detection': True,
                        'detection_types': len(templates),
                        'image_path': image_path
                    },
                    response_data={
                        'ai_response': result.get('ai_response', ''),
                        'confidence': result.get('confidence', 0.0),
                        'has_alert': result.get('has_alert', False)
                    },
                    response_time_ms=response_time_ms // len(templates),  # 平均分配响应时间
                    confidence_score=str(result.get('confidence', 0.0))
                )

            logger.info(
                f"✅ 帧{frame_index}复合检测完成: "
                f"检测{len(results)}种类型, 耗时{composite_result.get('response_time', 0)}s, "
                f"发现{sum(1 for r in results if r.get('has_alert'))}个告警"
            )

            return results

        except Exception as e:
            logger.error(f"帧{frame_index}复合检测异常: {e}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")

            # 返回错误结果
            return [{
                'frame_index': frame_index,
                'timestamp': timestamp,
                'template_id': template.get('id', 'unknown'),
                'template_name': template.get('name', 'unknown'),
                'category': template.get('category', 'unknown'),
                'image_url': minio_url or image_path,
                'has_alert': False,
                'ai_response': f"复合检测异常: {str(e)}",
                'confidence': 0.0,
                'error': str(e)
            } for template in templates]

    def _convert_violations_to_results(
        self,
        violations: List[Dict],
        templates: List[Dict],
        frame_index: int,
        timestamp: float,
        minio_url: str,
        composite_result: Dict
    ) -> List[Dict]:
        """将violations列表转换为results格式 - 委托给 helpers.video_frame_extractor"""
        return _convert_violations_helper(
            violations, templates, frame_index, timestamp, minio_url, composite_result
        )

    def _extract_violation_from_ai_response(self, ai_response: str) -> bool:
        """从AI多模态响应中提取违规信息 - 委托给 helpers.video_frame_extractor"""
        return _extract_violation_helper(ai_response)
    
    async def _sync_progress_to_db(self, video_id: str, progress_percentage: int):
        """将进度同步到数据库"""
        try:
            await VideoFileService.update_analysis_progress(video_id, progress_percentage)
            logger.debug(f"已同步进度到数据库: 视频={video_id}, 进度={progress_percentage}%")
        except Exception as e:
            logger.warning(f"同步进度到数据库失败: {e}")

    async def _update_task_status_in_es(self, task):
        """
        更新Elasticsearch中的任务状态
        修复任务完成后状态不同步的问题
        """
        try:
            from services.elasticsearch_service import elasticsearch_service
            from elasticsearch import NotFoundError

            # 构建状态更新数据
            update_data = {
                "status": task.status,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }

            # 如果任务失败，添加错误信息
            if task.status == "failed" and hasattr(task, 'error_message'):
                update_data["error_message"] = task.error_message

            # 如果任务完成，计算duration
            if task.status == "completed" and task.completed_at and task.started_at:
                update_data["duration"] = (task.completed_at - task.started_at).total_seconds()

            # 检查文档是否存在，不存在则跳过更新
            try:
                await elasticsearch_service.es_client.get(
                    index="video_analysis_results",
                    id=task.id
                )
            except NotFoundError:
                logger.warning(f"⚠️  任务文档不存在（可能分析失败未保存）: {task.id}, 跳过状态更新")
                return

            # 更新ES中的文档
            await elasticsearch_service.es_client.update(
                index="video_analysis_results",
                id=task.id,
                body={"doc": update_data},
                refresh=True
            )

            logger.info(f"✅ 已更新ES中的任务状态: {task.id} -> {task.status}")

        except Exception as e:
            logger.error(f"更新ES任务状态失败 {task.id}: {e}")


# 创建全局实例
video_analysis_service = VideoAnalysisService()