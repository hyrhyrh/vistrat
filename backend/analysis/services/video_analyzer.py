"""
视频分析器
负责协调整个视频分析流程
"""

import asyncio
import cv2
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from models.analysis_result import (
    VideoAnalysisResult, FrameAnalysisResult, AnnotationObject, 
    BoundingBox, AlertSeverity, DetectionType
)
from models.video_metadata import VideoAnalysisTask, AnalysisStatus
from services.ai_client import AIClient
from prompts.services.prompt_manager import PromptManager
from analysis.services.annotation_service import AnnotationService
from analysis.services.ai_response_parser import AIResponseParser
from analysis.services.analysis_summarizer import AnalysisSummarizer
from storage.services.minio_client import MinIOClient
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """视频分析器"""
    
    def __init__(self):
        self.ai_client = AIClient()
        self.prompt_manager = PromptManager()
        self.annotation_service = AnnotationService()
        self.response_parser = AIResponseParser()
        self.summarizer = AnalysisSummarizer()
        self.minio_client = MinIOClient()
        
    async def analyze_video(self, video_path: str, prompt_template_ids: List[str],
                          task: VideoAnalysisTask, progress_callback: Optional[Callable] = None) -> VideoAnalysisResult:
        """
        分析完整视频
        
        Args:
            video_path: 视频文件路径
            prompt_template_ids: 使用的提示词模板ID列表
            task: 分析任务对象
            progress_callback: 进度回调函数
            
        Returns:
            VideoAnalysisResult: 完整分析结果
        """
        logger.info(f"开始分析视频: {video_path}")
        
        try:
            # 打开视频文件
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                raise ValueError(f"无法打开视频文件: {video_path}")
            
            # 获取视频信息
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            # 获取分析模板
            templates = []
            for template_id in prompt_template_ids:
                template = await self.prompt_manager.get_template_by_id(template_id)
                if template:
                    templates.append(template)
            
            if not templates:
                raise ValueError("未找到有效的提示词模板")
            
            # 分析每一帧
            frame_results = []
            frame_index = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                timestamp = frame_index / fps
                
                # 分析当前帧
                frame_result = await self._analyze_frame(
                    frame, frame_index, timestamp, templates
                )
                
                if frame_result:
                    frame_results.append(frame_result)
                
                # 更新进度
                if progress_callback:
                    progress = (frame_index + 1) / total_frames
                    await progress_callback(progress, frame_index + 1, total_frames)
                
                frame_index += 1
                
                # 限制处理频率（可配置）
                if frame_index % 30 == 0:  # 每30帧处理一次
                    await asyncio.sleep(0.01)
            
            cap.release()
            
            # 生成最终结果
            result = await self.summarizer.create_video_analysis_result(
                task_id=task.task_id,
                video_path=str(video_path),
                frame_results=frame_results,
                template_ids=prompt_template_ids
            )
            
            logger.info(f"视频分析完成，共分析 {len(frame_results)} 帧")
            return result
            
        except Exception as e:
            logger.error(f"视频分析失败: {e}")
            raise
    
    async def _analyze_frame(self, frame, frame_index: int, timestamp: float,
                           templates: List[Any]) -> Optional[FrameAnalysisResult]:
        """分析单个视频帧"""
        try:
            all_objects = []
            
            # 使用所有模板分析帧
            for template in templates:
                objects = await self._analyze_frame_with_template(
                    frame, frame_index, timestamp, template
                )
                all_objects.extend(objects)
            
            if not all_objects:
                return None
            
            # 创建帧分析结果
            has_alerts = any(obj.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] 
                           for obj in all_objects)
            
            return FrameAnalysisResult(
                frame_index=frame_index,
                timestamp=timestamp,
                objects=all_objects,
                has_alerts=has_alerts,
                analysis_time=now_isoformat()
            )
            
        except Exception as e:
            logger.error(f"分析帧 {frame_index} 失败: {e}")
            return None
    
    async def _analyze_frame_with_template(self, frame, frame_index: int,
                                         timestamp: float, template) -> List[AnnotationObject]:
        """使用指定模板分析帧"""
        try:
            # 保存帧到临时文件
            temp_path = f"/tmp/frame_{frame_index}_{timestamp}.jpg"
            cv2.imwrite(temp_path, frame)
            
            # 渲染提示词
            context = {
                'frame_index': frame_index,
                'timestamp': timestamp,
                'video_time': f"{int(timestamp//60):02d}:{int(timestamp%60):02d}"
            }
            
            rendered_prompt = self.prompt_manager.render_prompt(template, context)
            
            # 调用AI分析
            ai_response = await self.ai_client.analyze_image_with_prompt(
                temp_path, rendered_prompt
            )
            
            # 解析AI响应
            objects = await self.response_parser.parse_ai_response(ai_response, template)
            
            # 清理临时文件
            Path(temp_path).unlink(missing_ok=True)
            
            return objects
            
        except Exception as e:
            logger.error(f"使用模板分析帧失败: {e}")
            return []