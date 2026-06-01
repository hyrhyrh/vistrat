"""
统一AI分析引擎 - 核心复用架构
同时处理本地视频和实时流，完全复用现有AI分析组件
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, AsyncIterator
from pathlib import Path

from services.stream_abstraction import StreamSource, StreamFrame, StreamFactory
from services.frame_analyzer import FrameAnalyzer
from services.analysis_result_processor import AnalysisResultProcessor
from services.video_analysis_template_service import video_analysis_template_service
from services.ai_analysis_log_service import ai_analysis_log_service
from services.storage import storage_service
from config.settings import PathConfig
from utils.timezone_utils import now

logger = logging.getLogger(__name__)


class UnifiedAnalysisTask:
    """统一的分析任务类 - 支持任何类型的数据源"""
    
    def __init__(self, source_id: str, source_type: str, template_ids: List[str]):
        self.id = str(uuid.uuid4())
        self.source_id = source_id
        self.source_type = source_type  # 'video_file' | 'rtsp_stream'
        self.template_ids = template_ids
        
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.progress = 0.0
        self.error_message = None
        self.results = []
        
        self.created_at = now()
        self.started_at = None
        self.completed_at = None
        
        # 实时任务特有属性
        self.frames_processed = 0
        self.alerts_generated = 0
        self.last_frame_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'source_id': self.source_id,
            'source_type': self.source_type,
            'template_ids': self.template_ids,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'frames_processed': self.frames_processed,
            'alerts_generated': self.alerts_generated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'last_frame_time': self.last_frame_time.isoformat() if self.last_frame_time else None,
            'results_count': len(self.results) if self.results else 0
        }


class UnifiedAnalysisEngine:
    """
    统一AI分析引擎 - Ultra重构核心
    完全复用现有FrameAnalyzer和AnalysisResultProcessor
    """
    
    def __init__(self):
        # 复用现有核心组件
        self.frame_analyzer = FrameAnalyzer()
        self.result_processor = AnalysisResultProcessor()
        
        # 任务管理
        self.running_tasks: Dict[str, UnifiedAnalysisTask] = {}
        self.task_streams: Dict[str, StreamSource] = {}
        
        # 性能监控
        self.total_frames_analyzed = 0
        self.total_alerts_generated = 0
    
    async def start_analysis(self, source_type: str, source_path: str, 
                           template_ids: Optional[List[str]] = None,
                           source_id: Optional[str] = None,
                           analysis_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        启动统一分析 - 支持任何类型的数据源
        
        Args:
            source_type: 'video_file' | 'rtsp_stream'
            source_path: 文件路径或RTSP URL
            template_ids: AI算法模板ID列表
            source_id: 数据源ID（视频ID或流ID）
            analysis_config: 分析配置参数
        """
        try:
            # 生成source_id（如果未提供）
            if not source_id:
                source_id = f"{source_type}_{int(now().timestamp())}"
            
            # 获取AI算法模板
            if not template_ids:
                if source_type == 'video_file':
                    # 本地视频：从数据库获取配置
                    templates = await video_analysis_template_service.get_video_analysis_templates(source_id)
                    if not templates:
                        raise ValueError("请先配置视频分析算法")
                    template_ids = [t['id'] for t in templates if t.get('enabled', True)]
                else:
                    # 实时流：使用默认算法或从配置获取
                    if not template_ids:
                        raise ValueError("实时流必须指定分析算法")
            
            if not template_ids:
                raise ValueError("没有可用的分析算法")
            
            # 创建统一分析任务
            task = UnifiedAnalysisTask(source_id, source_type, template_ids)
            self.running_tasks[task.id] = task
            
            # 创建数据源
            stream_source = StreamFactory.create_stream(source_type, source_id, source_path)
            self.task_streams[task.id] = stream_source
            
            # 获取分析配置
            config = analysis_config or {}
            frame_interval = config.get('frame_interval', 5.0)  # 默认5秒采样
            
            logger.info(f"启动统一分析任务: {task.id}, 类型: {source_type}, 源: {source_path}")
            
            # 异步执行分析
            asyncio.create_task(self._execute_analysis_task(task, stream_source, frame_interval))
            
            return {
                'task_id': task.id,
                'source_id': source_id,
                'source_type': source_type,
                'template_count': len(template_ids),
                'status': 'queued',
                'frame_interval': frame_interval
            }
            
        except Exception as e:
            logger.error(f"启动统一分析失败: {e}")
            raise
    
    async def _execute_analysis_task(self, task: UnifiedAnalysisTask, 
                                   stream_source: StreamSource, frame_interval: float):
        """执行分析任务 - 核心处理逻辑"""
        try:
            task.status = "running"
            task.started_at = now()
            
            logger.info(f"开始执行分析任务: {task.id}, 类型: {task.source_type}")
            
            # 初始化数据源
            if not await stream_source.initialize():
                raise ValueError("数据源初始化失败")
            
            # 获取AI算法模板
            templates = await self._get_analysis_templates(task.template_ids)
            if not templates:
                raise ValueError("无法获取有效的AI算法模板")
            
            # 创建临时目录
            temp_dir = Path(PathConfig.TEMP_DIR) / f"analysis_{task.id}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # 设置当前任务上下文
            self.current_task_id = task.id
            self.current_source_id = task.source_id
            
            # 分析帧流
            results = []
            async for frame in stream_source.produce_frames(frame_interval):
                if task.status == "cancelled":
                    logger.info(f"任务被取消: {task.id}")
                    break
                
                try:
                    # 分析单帧（完全复用现有逻辑）
                    frame_results = await self._analyze_single_frame(frame, templates, temp_dir)
                    
                    if frame_results:
                        results.extend(frame_results)
                        task.frames_processed += 1
                        task.last_frame_time = now()
                        
                        # 实时流：增量处理结果
                        if task.source_type == 'rtsp_stream':
                            await self._process_realtime_results(task, frame_results)
                        
                        # 统计告警
                        alert_count = sum(1 for r in frame_results if r.get('has_alert', False))
                        task.alerts_generated += alert_count
                        
                        logger.debug(f"帧 {frame.frame_index} 分析完成，生成 {len(frame_results)} 个结果，{alert_count} 个告警")
                    
                    # 更新进度
                    if task.source_type == 'video_file':
                        # 本地视频：基于总帧数计算进度
                        source_info = stream_source.get_source_info()
                        total_frames = source_info.get('total_frames', 1)
                        task.progress = min(frame.frame_index / total_frames, 1.0)
                    else:
                        # 实时流：基于处理时间计算活跃度
                        task.progress = min(task.frames_processed / 100.0, 1.0)  # 最多显示100%
                    
                except Exception as e:
                    logger.error(f"分析帧 {frame.frame_index} 失败: {e}")
                    continue
            
            # 任务完成处理
            await self._finalize_analysis_task(task, results, temp_dir)
            
        except Exception as e:
            logger.error(f"执行分析任务失败 {task.id}: {e}")
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = now()
        finally:
            # 清理资源
            await self._cleanup_task_resources(task.id)
    
    async def _analyze_single_frame(self, frame: StreamFrame, templates: List[Any], 
                                  temp_dir: Path) -> List[Dict[str, Any]]:
        """
        分析单帧 - 完全复用现有AI分析逻辑
        这是从原VideoAnalysisService抽离的核心逻辑
        """
        try:
            # 保存帧到临时文件
            frame_path = frame.save_to_temp(temp_dir)
            
            # 上传到MinIO
            minio_url = await storage_service.upload_frame_image(
                frame_path, self.current_task_id, frame.frame_index
            )
            
            results = []
            
            # 对每个AI算法模板进行分析
            for template in templates:
                start_time = None
                call_success = False
                analysis_result = None
                error_message = None
                
                try:
                    prompt = template['prompt_content']
                    # 构建完整的算法名称："违规行为分析 - {display_name}"
                    full_algorithm_name = f"违规行为分析 - {template['name']}"

                    logger.debug(f"使用算法 '{full_algorithm_name}' 分析帧 {frame.frame_index}")

                    # 准备请求数据
                    request_data = {
                        'image_path': frame_path,
                        'prompt': prompt,
                        'frame_index': frame.frame_index,
                        'timestamp': frame.timestamp,
                        'algorithm_name': full_algorithm_name,  # 使用完整算法名称
                        'algorithm_category': template['category']
                    }
                    
                    # 记录开始时间
                    import time
                    start_time = time.time()
                    
                    # AI分析（完全复用FrameAnalyzer）
                    analysis_result = await self.frame_analyzer.analyze_frame_with_ai(
                        frame_path, prompt
                    )
                    
                    response_time_ms = int((time.time() - start_time) * 1000)
                    call_success = True
                    
                    # 记录成功的AI调用日志
                    await ai_analysis_log_service.log_success_call(
                        task_id=str(self.current_task_id),
                        video_id=str(self.current_source_id),
                        algorithm_id=template['id'],
                        algorithm_config_id=template.get('template_id', template['id']),
                        model_name=analysis_result.get('model_used', 'unknown'),
                        frame_index=frame.frame_index,
                        frame_timestamp=str(frame.timestamp),
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
                    
                    # 检测违规（复用现有逻辑）
                    has_alert = self._extract_violation_from_ai_response(
                        analysis_result['ai_response']
                    )

                    result = {
                        'frame_index': frame.frame_index,
                        'timestamp': frame.timestamp,
                        'real_timestamp': frame.real_timestamp.isoformat(),
                        'template_id': template['id'],
                        'template_name': full_algorithm_name,  # 使用完整算法名称
                        'category': template['category'],
                        'priority': template.get('priority', 0),
                        'has_alert': has_alert,
                        'source_type': frame.source_type,
                        **analysis_result,
                        'image_path': minio_url or frame_path,
                    }
                    
                    results.append(result)
                    
                    self.total_frames_analyzed += 1
                    if has_alert:
                        self.total_alerts_generated += 1
                    
                except Exception as e:
                    logger.error(f"分析帧 {frame.frame_index} 算法 {template['name']} 失败: {e}")
                    error_message = str(e)
                    
                    # 记录失败日志
                    response_time_ms = None
                    if start_time:
                        response_time_ms = int((time.time() - start_time) * 1000)
                    
                    await ai_analysis_log_service.log_failed_call(
                        task_id=str(self.current_task_id),
                        video_id=str(self.current_source_id),
                        algorithm_id=template['id'],
                        algorithm_config_id=template.get('template_id', template['id']),
                        model_name='unknown',
                        frame_index=frame.frame_index,
                        frame_timestamp=str(frame.timestamp),
                        request_data=request_data if 'request_data' in locals() else {},
                        error_message=error_message,
                        error_code='ANALYSIS_ERROR',
                        response_time_ms=response_time_ms
                    )
            
            return results
            
        except Exception as e:
            logger.error(f"分析单帧失败 {frame.frame_index}: {e}")
            return []
    
    def _extract_violation_from_ai_response(self, ai_response: str) -> bool:
        """从AI响应中提取违规信息（复用现有逻辑）"""
        try:
            import json
            import re
            
            # JSON解析
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                try:
                    response_data = json.loads(json_str)
                    if 'has_violation' in response_data:
                        return bool(response_data['has_violation'])
                    elif 'violation_count' in response_data:
                        return int(response_data.get('violation_count', 0)) > 0
                except json.JSONDecodeError:
                    pass
            
            # 关键词检查
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
    
    async def _process_realtime_results(self, task: UnifiedAnalysisTask, frame_results: List[Dict[str, Any]]):
        """实时处理结果 - 增量存储和告警"""
        try:
            # 实时流：立即处理每帧结果
            if frame_results:
                # 存储到ES（增量）
                await self._store_frame_results_to_elasticsearch(task, frame_results)
                
                # 生成实时告警
                await self._generate_realtime_alerts(task, frame_results)
                
        except Exception as e:
            logger.error(f"实时结果处理失败: {e}")
    
    async def _finalize_analysis_task(self, task: UnifiedAnalysisTask, 
                                    results: List[Dict[str, Any]], temp_dir: Path):
        """完成分析任务"""
        try:
            task.results = results
            
            if task.source_type == 'video_file':
                # 本地视频：批量处理所有结果
                await self.result_processor.process_analysis_results(task, results)
            else:
                # 实时流：生成汇总报告
                await self._generate_realtime_summary(task, results)
            
            task.status = "completed"
            task.completed_at = now()
            task.progress = 1.0
            
            logger.info(f"分析任务完成: {task.id}, 处理 {task.frames_processed} 帧，生成 {task.alerts_generated} 个告警")
            
        except Exception as e:
            logger.error(f"完成分析任务失败: {e}")
            task.status = "failed"
            task.error_message = str(e)
        finally:
            # 清理临时文件
            try:
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
    
    async def _get_analysis_templates(self, template_ids: List[str]) -> List[Any]:
        """获取AI算法模板"""
        try:
            # 这里需要根据template_ids获取模板
            # 暂时返回空列表，实际使用时需要连接数据库
            templates = []
            for template_id in template_ids:
                # 从数据库或配置中获取模板
                pass
            return templates
        except Exception as e:
            logger.error(f"获取AI算法模板失败: {e}")
            return []
    
    async def stop_analysis(self, task_id: str) -> bool:
        """停止分析任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = "cancelled"
            task.completed_at = now()
            
            logger.info(f"分析任务已停止: {task_id}")
            return True
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.running_tasks.get(task_id)
        if not task:
            return None
        
        # 获取数据源信息
        stream_info = {}
        if task_id in self.task_streams:
            stream_info = self.task_streams[task_id].get_source_info()
        
        status = task.to_dict()
        status['stream_info'] = stream_info
        return status
    
    async def _cleanup_task_resources(self, task_id: str):
        """清理任务资源"""
        try:
            # 清理数据源
            if task_id in self.task_streams:
                await self.task_streams[task_id].cleanup()
                del self.task_streams[task_id]
            
            # 从运行任务中移除（保留一定时间用于状态查询）
            # 这里可以实现LRU清理策略
            
        except Exception as e:
            logger.error(f"清理任务资源失败: {e}")
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        return {
            'running_tasks': len(self.running_tasks),
            'total_frames_analyzed': self.total_frames_analyzed,
            'total_alerts_generated': self.total_alerts_generated,
            'active_streams': len(self.task_streams)
        }


# 创建全局实例
unified_analysis_engine = UnifiedAnalysisEngine()