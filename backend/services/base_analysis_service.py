"""
基础AI分析服务 - 抽离可复用的组件
为本地视频流和实时流提供统一的AI分析能力
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.timezone_utils import now, now_isoformat

from services.frame_analyzer import FrameAnalyzer
from services.analysis_result_processor import AnalysisResultProcessor
from services.ai_analysis_log_service import ai_analysis_log_service

logger = logging.getLogger(__name__)


class BaseAnalysisTask:
    """基础分析任务类"""
    
    def __init__(self, task_id: str, source_id: str, template_ids: List[str], task_type: str = 'unknown'):
        self.id = task_id
        self.source_id = source_id  # 视频ID或实时流ID
        self.template_ids = template_ids
        self.task_type = task_type  # 'video', 'realtime_stream'
        
        self.status = "pending"
        self.progress = 0.0
        self.error_message = None
        self.results = []
        
        self.created_at = now()
        self.started_at = None
        self.completed_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'source_id': self.source_id,
            'task_type': self.task_type,
            'template_ids': self.template_ids,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'results_count': len(self.results) if self.results else 0
        }


class BaseAnalysisService(ABC):
    """基础分析服务抽象类"""
    
    def __init__(self):
        # 共享的核心组件
        self.frame_analyzer = FrameAnalyzer()
        self.result_processor = AnalysisResultProcessor()
        
        # 当前任务上下文 - 用于日志记录
        self.current_task_id = None
        self.current_source_id = None
    
    @abstractmethod
    async def start_analysis(self, source_id: str, template_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """启动分析 - 子类必须实现"""
        pass
    
    @abstractmethod
    async def stop_analysis(self, task_id: str) -> bool:
        """停止分析 - 子类必须实现"""
        pass
    
    async def analyze_single_frame_with_templates(self, frame_index: int, timestamp: float,
                                                templates: List[Any], image_path: str, 
                                                minio_url: str = None) -> List[Dict[str, Any]]:
        """
        使用多个AI算法模板分析单帧
        这是从原VideoAnalysisService中抽离的核心分析逻辑
        """
        try:
            results = []
            
            # 对每个分析算法进行分析
            for template in templates:
                start_time = None
                call_success = False
                analysis_result = None
                error_message = None
                
                try:
                    # 直接使用数据库中的prompt_content
                    prompt = template['prompt_content']
                    
                    logger.debug(f"使用算法 '{template['name']}' 分析帧 {frame_index}")
                    
                    # 准备请求数据用于日志记录
                    request_data = {
                        'image_path': image_path,
                        'prompt': prompt,
                        'frame_index': frame_index,
                        'timestamp': timestamp,
                        'algorithm_name': template['name'],
                        'algorithm_category': template['category']
                    }
                    
                    # 记录开始时间
                    start_time = time.time()
                    
                    # AI分析
                    analysis_result = await self.frame_analyzer.analyze_frame_with_ai(
                        image_path, prompt
                    )
                    
                    # 计算响应时间
                    response_time_ms = int((time.time() - start_time) * 1000)
                    call_success = True
                    
                    # 记录成功的AI调用日志
                    await ai_analysis_log_service.log_success_call(
                        task_id=str(self.current_task_id or 'unknown'),
                        video_id=str(self.current_source_id or 'unknown'),
                        algorithm_id=template['id'],
                        algorithm_config_id=template.get('template_id', template['id']),
                        model_name=analysis_result.get('model_used', 'unknown'),
                        frame_index=frame_index,
                        frame_timestamp=str(timestamp),
                        request_data=request_data,
                        response_data={
                            'ai_response': analysis_result.get('ai_response', ''),
                            'confidence': analysis_result.get('confidence', ''),
                            'model_used': analysis_result.get('model_used', ''),
                            'processing_info': analysis_result.get('processing_info', {})
                        },
                        response_time_ms=response_time_ms,
                        confidence_score=str(analysis_result.get('confidence', ''))
                    )
                    
                    # 解析AI响应中的违规信息
                    has_alert = self._extract_violation_from_ai_response(
                        analysis_result['ai_response']
                    )
                    
                    result = {
                        'frame_index': frame_index,
                        'timestamp': timestamp,
                        'template_id': template['id'],
                        'template_name': template['name'],
                        'category': template['category'],
                        'priority': template.get('priority', 0),
                        'has_alert': has_alert,
                        **analysis_result,
                        'image_path': minio_url or image_path,  # 优先使用MinIO URL
                    }
                    
                    results.append(result)
                    
                    logger.debug(f"帧 {frame_index} 算法 {template['name']} 分析完成, 告警: {has_alert}")
                    
                except Exception as e:
                    logger.error(f"分析帧 {frame_index} 算法 {template['name']} 失败: {e}")
                    error_message = str(e)
                    
                    # 记录失败的AI调用日志
                    response_time_ms = None
                    if start_time:
                        response_time_ms = int((time.time() - start_time) * 1000)
                    
                    await ai_analysis_log_service.log_failed_call(
                        task_id=str(self.current_task_id or 'unknown'),
                        video_id=str(self.current_source_id or 'unknown'),
                        algorithm_id=template['id'],
                        algorithm_config_id=template.get('template_id', template['id']),
                        model_name='unknown',
                        frame_index=frame_index,
                        frame_timestamp=str(timestamp),
                        request_data=request_data if 'request_data' in locals() else {},
                        error_message=error_message,
                        error_code='ANALYSIS_ERROR',
                        response_time_ms=response_time_ms
                    )
                    
                    # 添加错误结果
                    results.append({
                        'frame_index': frame_index,
                        'timestamp': timestamp,
                        'template_id': template['id'],
                        'template_name': template['name'],
                        'category': template['category'],
                        'image_path': minio_url or image_path,
                        'has_alert': False,
                        'ai_response': f"分析失败: {str(e)}",
                        'confidence': 0.0,
                        'error': str(e)
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"分析单帧失败 {frame_index}: {e}")
            return []
    
    def _extract_violation_from_ai_response(self, ai_response: str) -> bool:
        """
        从AI多模态响应中提取违规信息
        共享的违规检测逻辑
        """
        try:
            import json
            import re
            # 尝试从响应中提取JSON部分
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    response_data = json.loads(json_str)
                    # 检查has_violation字段
                    if 'has_violation' in response_data:
                        return bool(response_data['has_violation'])
                    # 检查violation_count字段，大于0表示有违规
                    elif 'violation_count' in response_data:
                        return int(response_data.get('violation_count', 0)) > 0
                except json.JSONDecodeError as e:
                    logger.warning(f"解析AI响应JSON失败: {e}")
            
            # 降级到关键词检查
            response_lower = ai_response.lower()
            violation_keywords = [
                'has_violation": true', '"has_violation":true',
                '违规', '违反', '异常', '不规范', '不合规',
                'violation', 'violate', 'alert', 'warning'
            ]
            
            return any(keyword in response_lower for keyword in violation_keywords)
            
        except Exception as e:
            logger.warning(f"提取违规信息失败: {e}")
            return False
    
    async def process_and_store_results(self, task: BaseAnalysisTask, results: List[Dict[str, Any]]):
        """
        处理和存储分析结果
        共享的结果处理逻辑
        """
        try:
            if not results:
                logger.warning(f"任务 {task.id} 没有分析结果")
                return
            
            # 设置任务结果
            task.results = results
            
            # 使用共享的结果处理器
            await self.result_processor.process_analysis_results(task, results)
            
            logger.info(f"成功处理 {len(results)} 个分析结果")
            
        except Exception as e:
            logger.error(f"处理分析结果失败: {e}")
            raise