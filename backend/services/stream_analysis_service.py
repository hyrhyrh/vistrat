"""
实时视频流分析服务
负责管理多个视频流的实时AI分析任务
基于离线视频分析架构，优化实时流处理性能

# FIXME(circular): 与 stream_task_manager 存在循环依赖，当前通过延迟导入规避。
# stream_analysis_service 在 start/stop 时需要查询 stream_task_manager 的任务列表，
# stream_task_manager 在 start/stop 时需要调用 stream_analysis_service 的分析控制。
# 建议重构: 提取 StreamTaskCoordinator 协调层，两者都不直接引用对方。
"""

import asyncio
import logging
from datetime import datetime
from utils.timezone_utils import now, now_isoformat
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from services.stream_frame_analyzer import stream_frame_analyzer
from services.video_analysis_template_service import video_analysis_template_service
from services.analysis_result_processor import AnalysisResultProcessor
from services.elasticsearch_service import elasticsearch_service
from services.helpers.buffer_manager import (
    flush_buffered_data as _flush_buffered_data_helper,
    save_frame_results_to_elasticsearch as _save_frame_results_helper,
    save_alerts_to_elasticsearch as _save_alerts_helper,
    adaptive_flush_callback as _adaptive_flush_callback_helper,
)
from services.video_stream_service import VideoStreamService
from services.adaptive_buffer_manager import adaptive_buffer_manager

logger = logging.getLogger(__name__)


@dataclass
class StreamAnalysisTask:
    """实时流分析任务数据结构"""
    task_id: str
    stream_id: str
    stream_name: str
    rtsp_url: str
    template_ids: List[str]
    status: str = "pending"  # pending, running, stopped, error
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    frame_count: int = 0
    alert_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        # 处理datetime序列化
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.stopped_at:
            data['stopped_at'] = self.stopped_at.isoformat()
        return data


class StreamAnalysisService:
    """实时视频流分析服务"""
    
    def __init__(self):
        self.running_tasks: Dict[str, StreamAnalysisTask] = {}
        self.result_processor = AnalysisResultProcessor()
        self._frame_results_buffer = {}  # 帧结果缓冲区（保留向后兼容）
        self._alerts_buffer = {}  # 告警缓冲区（保留向后兼容）
        self._background_processor_started = False
        
        # 集成自适应缓冲区管理器
        adaptive_buffer_manager.set_flush_callback(self._adaptive_flush_callback)
    
    def _start_background_processors(self):
        """启动后台数据处理器 - 延迟到事件循环可用时"""
        if not self._background_processor_started:
            try:
                # 启动自适应缓冲区管理器
                asyncio.create_task(adaptive_buffer_manager.start_adaptive_flushing())
                # 保留原有批量处理器作为备用
                asyncio.create_task(self._batch_process_results())
                self._background_processor_started = True
                logger.info("后台数据处理器已启动（包含自适应缓冲区管理器）")
            except RuntimeError:
                # 事件循环还未启动，稍后再尝试
                logger.debug("事件循环未启动，将在首次调用时启动后台处理器")
                pass
    
    async def start_stream_analysis(self, stream_id: str) -> Dict[str, Any]:
        """启动视频流实时分析"""
        try:
            # 确保后台处理器已启动
            self._start_background_processors()
            # 检查是否已有正在运行的任务
            existing_task = None
            for task in self.running_tasks.values():
                if task.stream_id == stream_id and task.status == "running":
                    existing_task = task
                    break
            
            if existing_task:
                logger.warning(f"流 {stream_id} 已有正在运行的分析任务: {existing_task.task_id}")
                # 获取template数量（修复：添加template_count字段）
                template_count = len(existing_task.template_ids) if hasattr(existing_task, 'template_ids') and existing_task.template_ids else 0
                return {
                    'task_id': existing_task.task_id,
                    'stream_id': stream_id,
                    'status': 'already_running',
                    'template_count': template_count,
                    'message': '该视频流已有正在运行的分析任务'
                }
            
            # 获取流配置信息
            stream_config = await VideoStreamService.get_stream_configuration(stream_id)
            if not stream_config:
                raise ValueError(f"未找到流配置: {stream_id}")
            
            stream_name = stream_config.get('name', f'Stream_{stream_id}')
            rtsp_url = stream_config.get('rtsp_url', '')
            
            if not rtsp_url:
                raise ValueError(f"流 {stream_id} 缺少RTSP地址")

            # 🔧 优化：启动分析时不执行RTSP流健康检查，提升前端交互体验
            # 健康检查将在实际分析任务执行时进行（stream_frame_analyzer中）
            # 如果流异常，本次分析会自动结束，等待下次重试或定时调度
            logger.info(f"启动分析任务，跳过RTSP流健康预检查: {rtsp_url}")

            # 获取分析模板配置
            analysis_config = await VideoStreamService.get_analysis_templates(stream_id)
            if not analysis_config.get('success') or not analysis_config.get('templates'):
                # 提示用户需要先配置分析算法
                error_msg = f"流 {stream_id} 未配置分析算法，请先在前端选择AI算法并保存配置"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            template_ids = [t['template_id'] for t in analysis_config['templates']]

            # 从数据库查询实际的AI算法配置
            templates = []
            for template_config in analysis_config['templates']:
                template_id = template_config['template_id']

                # 从ai_model_configs表查询算法详细配置
                try:
                    from database.connection import DatabaseManager
                    from sqlalchemy import text

                    async with DatabaseManager.get_session() as db:
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
                            # 获取检测能力列表
                            detection_capabilities = row[12] if row[12] else []

                            # 构建完整的模板配置，使用数据库中的实际配置
                            template = {
                                'id': str(row[0]),
                                'name': row[1],  # 使用实际的算法名称
                                'description': row[2],
                                'category': template_config.get('category', 'safety_monitoring'),
                                'priority': template_config.get('priority', 1),
                                'confidence_threshold': template_config.get('confidence_threshold', row[10]),

                                # AI模型配置
                                'provider': row[3],
                                'model_name': row[4],
                                'system_prompt': row[5],  # 使用数据库中配置的system_prompt
                                'user_prompt': row[6],    # 使用数据库中配置的user_prompt
                                'temperature': float(row[7]) if row[7] else 0.7,
                                'top_p': float(row[8]) if row[8] else 0.9,
                                'max_tokens': row[9] if row[9] else 1000,

                                # 复合检测配置（新增）
                                'detection_capabilities': detection_capabilities,

                                # 用于向后兼容stream_frame_analyzer的字段
                                'prompt_content': row[6] if row[6] else row[5]  # 优先使用user_prompt，否则使用system_prompt
                            }
                            templates.append(template)

                            # 日志输出检测能力信息
                            if detection_capabilities:
                                logger.info(f"已加载算法配置: {template['name']} (ID: {template_id[:8]}...), 检测能力: {detection_capabilities}")
                            else:
                                logger.info(f"已加载算法配置: {template['name']} (ID: {template_id[:8]}...)")
                        else:
                            logger.error(f"未找到算法配置: template_id={template_id}")

                except Exception as e:
                    logger.error(f"查询算法配置失败: template_id={template_id}, 错误={e}")

            if not templates:
                raise ValueError(f"未能加载任何有效的算法配置，请检查ai_model_configs表中是否存在对应的算法")

            logger.info(f"为流 {stream_id} 成功加载了 {len(templates)} 个AI算法配置")
            
            # 创建分析任务
            task_id = f"stream_task_{stream_id}_{int(now().timestamp())}"
            task = StreamAnalysisTask(
                task_id=task_id,
                stream_id=stream_id,
                stream_name=stream_name,
                rtsp_url=rtsp_url,
                template_ids=template_ids,
                status="running",
                started_at=now()
            )
            
            self.running_tasks[task_id] = task
            
            # 查询该流已启用的分析任务，获取task_id并关联到template，同时检查时间配置
            try:
                from services.stream_task_manager import stream_task_manager
                from uuid import UUID
                from utils.time_config_checker import check_should_run_now, format_time_config_summary

                # 获取该流的所有任务
                tasks = await stream_task_manager.get_task_list(stream_id=stream_id)

                # 将任务按algorithm_config_id建立索引，方便快速查找
                # 注意：这里的algorithm_config_id是video_stream_algorithm_configs.id
                task_map = {}
                for task in tasks:
                    if task.get('is_active'):  # 只处理is_active=true的任务
                        # 从stream_analysis_tasks查询关联的video_stream_algorithm_configs
                        algo_config_id = task.get('algorithm_config_id')
                        if algo_config_id:
                            task_map[algo_config_id] = task

                # 为每个template关联其对应的task_id，并检查时间配置
                from database.connection import DatabaseManager
                from sqlalchemy import text

                templates_to_run = []  # 存储允许运行的模板

                async with DatabaseManager.get_session() as db:
                    for template in templates:
                        template_id = template['id']  # 这是ai_model_configs.id

                        # 查询video_stream_algorithm_configs和时间配置，找到关联的task
                        query = text("""
                            SELECT vsac.id, sat.id as task_id, sat.time_config, sat.task_name
                            FROM video_stream_algorithm_configs vsac
                            LEFT JOIN stream_analysis_tasks sat ON vsac.id = sat.algorithm_config_id
                            WHERE vsac.stream_id = :stream_id
                              AND vsac.template_id = :template_id
                              AND vsac.is_active = true
                              AND sat.is_active = true
                        """)
                        result = await db.execute(query, {
                            'stream_id': UUID(stream_id),
                            'template_id': template_id
                        })
                        row = result.fetchone()

                        if row and row[1]:
                            task_id_str = str(row[1])
                            time_config = row[2]  # JSONB字段
                            task_name = row[3]

                            template['task_id'] = task_id_str

                            # 检查时间配置
                            should_run, reason = check_should_run_now(time_config)

                            if should_run:
                                templates_to_run.append(template)
                                time_summary = format_time_config_summary(time_config)
                                logger.info(f"✓ 任务允许运行: {task_name}, "
                                          f"算法={template['name']}, "
                                          f"时间配置={time_summary}, "
                                          f"原因={reason}")
                            else:
                                time_summary = format_time_config_summary(time_config)
                                logger.warning(f"✗ 任务不在运行时间内，跳过: {task_name}, "
                                             f"算法={template['name']}, "
                                             f"时间配置={time_summary}, "
                                             f"原因={reason}")
                        else:
                            # 如果没有找到task，使用stream_id作为标识
                            template['task_id'] = f"notask_{template_id}"
                            logger.warning(f"未找到活跃任务: 算法={template['name']}, 使用临时task_id")
                            # 没有时间配置的任务默认允许运行
                            templates_to_run.append(template)

                # 更新templates列表为过滤后的列表
                templates = templates_to_run

                if not templates:
                    raise ValueError(f"流 {stream_id} 的所有任务都不在允许的运行时间范围内，无法启动分析")

                logger.info(f"经过时间配置过滤，{len(templates)} 个任务允许运行")

            except ValueError as ve:
                # 【修复】ValueError表示业务逻辑错误（如时间配置不匹配），必须重新抛出
                # 不应该继续执行，否则会启动template_count=0的空任务
                raise ve
            except Exception as e:
                # 【修复】只捕获其他异常（如数据库查询失败），并设置临时task_id继续运行
                logger.warning(f"查询任务task_id或检查时间配置失败: {e}")
                # 如果查询失败，为每个template设置临时task_id
                for template in templates:
                    if 'task_id' not in template:
                        template['task_id'] = f"error_task_{template['id']}"
            
            # 初始化缓冲区
            self._frame_results_buffer[stream_id] = []
            self._alerts_buffer[stream_id] = []
            
            # 收集所有任务的时间配置(用于帧分析器运行时检查)
            time_configs = {}
            for template in templates:
                task_id_from_template = template.get('task_id')
                # 跳过临时task_id（以notask_开头的）
                if task_id_from_template and not task_id_from_template.startswith('notask_'):
                    # 从数据库查询该任务的时间配置
                    async with DatabaseManager.get_session() as db:
                        time_query = text("""
                            SELECT sat.time_config
                            FROM stream_analysis_tasks sat
                            WHERE sat.id = :task_id
                        """)
                        time_result = await db.execute(time_query, {'task_id': task_id_from_template})
                        time_row = time_result.fetchone()
                        if time_row and time_row[0]:
                            time_configs[task_id_from_template] = time_row[0]

            # 启动实时流分析(传递时间配置)
            session_id = await stream_frame_analyzer.start_stream_analysis(
                rtsp_url=rtsp_url,
                stream_id=stream_id,
                templates=templates,
                time_configs=time_configs,  # 传递时间配置字典
                frame_callback=self._handle_frame_result,
                alert_callback=self._handle_alert
            )
            
            logger.info(f"实时流分析已启动: 任务={task_id}, 流={stream_id}, 会话={session_id}")
            
            return {
                'task_id': task_id,
                'session_id': session_id,
                'stream_id': stream_id,
                'stream_name': stream_name,
                'template_count': len(templates),
                'status': 'running'
            }
            
        except Exception as e:
            logger.error(f"启动实时流分析失败: {e}")
            # 清理running_tasks中的任务对象（修复：避免任务泄漏）
            try:
                if 'task_id' in locals() and task_id in self.running_tasks:
                    del self.running_tasks[task_id]
                    logger.info(f"已清理失败任务: {task_id}")
            except Exception as cleanup_error:
                logger.error(f"清理失败任务时出错: {cleanup_error}")
            raise
    
    async def stop_stream_analysis(self, stream_id: str) -> Dict[str, Any]:
        """停止视频流实时分析"""
        try:
            # 查找对应的任务
            task_to_stop = None
            for task in self.running_tasks.values():
                if task.stream_id == stream_id and task.status == "running":
                    task_to_stop = task
                    break
            
            if not task_to_stop:
                return {
                    'stream_id': stream_id,
                    'status': 'not_found',
                    'message': '未找到正在运行的分析任务'
                }
            
            # 停止帧分析器
            success = await stream_frame_analyzer.stop_stream_analysis(stream_id=stream_id)
            
            # 更新任务状态
            task_to_stop.status = "stopped"
            task_to_stop.stopped_at = now()
            
            # 同时停止StreamTaskManager中对应的任务
            try:
                from services.stream_task_manager import stream_task_manager
                
                # 查找并停止StreamTaskManager中对应stream_id的任务
                tasks = await stream_task_manager.get_task_list(stream_id=stream_id)
                for task in tasks:
                    if task.get('is_running', False):
                        await stream_task_manager.stop_analysis(task['id'])
                        logger.info(f"已停止StreamTaskManager中的任务: {task['id']}")
                        
            except Exception as e:
                logger.warning(f"停止StreamTaskManager中的任务失败: {e}")
            
            # 立即处理剩余的缓冲数据
            await self._flush_buffered_data(stream_id)

            # 从running_tasks字典中删除已停止的任务（修复：避免重复启动检测）
            if task_to_stop.task_id in self.running_tasks:
                del self.running_tasks[task_to_stop.task_id]
                logger.info(f"已从running_tasks中删除任务: {task_to_stop.task_id}")

            logger.info(f"实时流分析已停止: 任务={task_to_stop.task_id}, 流={stream_id}")

            return {
                'task_id': task_to_stop.task_id,
                'stream_id': stream_id,
                'status': 'stopped',
                'frame_count': task_to_stop.frame_count,
                'alert_count': task_to_stop.alert_count
            }
            
        except Exception as e:
            logger.error(f"停止实时流分析失败: {e}")
            raise
    
    async def get_stream_analysis_status(self, stream_id: str) -> Dict[str, Any]:
        """获取视频流分析状态"""
        try:
            # 查找对应的任务
            current_task = None
            for task in self.running_tasks.values():
                if task.stream_id == stream_id:
                    current_task = task
                    break
            
            if not current_task:
                return {
                    'stream_id': stream_id,
                    'status': 'not_found',
                    'message': '未找到分析任务'
                }
            
            # 获取帧分析器状态
            analyzer_status = stream_frame_analyzer.get_analysis_status()
            
            result = current_task.to_dict()
            if analyzer_status:
                result.update({
                    'analyzer_status': analyzer_status.get('status'),
                    'is_analyzing': analyzer_status.get('is_analyzing', False)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"获取流分析状态失败: {e}")
            return {
                'stream_id': stream_id,
                'status': 'error',
                'error': str(e)
            }
    
    def _handle_frame_result(self, frame_result: Dict[str, Any]):
        """处理帧分析结果回调"""
        try:
            stream_id = frame_result.get('stream_id')
            if not stream_id:
                return
            
            # 使用自适应缓冲区管理器
            buffer_key = f"frame_results_{stream_id}"
            adaptive_buffer_manager.add_item(buffer_key, frame_result)
            
            # 保留向后兼容的缓冲区（作为备用）
            if stream_id not in self._frame_results_buffer:
                self._frame_results_buffer[stream_id] = []
            self._frame_results_buffer[stream_id].append(frame_result)
            
            # 更新任务帧计数
            for task in self.running_tasks.values():
                if task.stream_id == stream_id and task.status == "running":
                    task.frame_count += 1
                    break
            
            # 更新系统负载信息
            active_streams = len([t for t in self.running_tasks.values() if t.status == "running"])
            adaptive_buffer_manager.update_system_load(active_streams)
            
            logger.debug(f"收到帧分析结果: 流={stream_id}, 帧={frame_result.get('frame_index')}")
            
        except Exception as e:
            logger.error(f"处理帧分析结果失败: {e}")
    
    def _handle_alert(self, alert_data: Dict[str, Any]):
        """处理告警回调"""
        try:
            stream_id = alert_data.get('stream_id')
            if not stream_id:
                return
            
            # 使用自适应缓冲区管理器
            buffer_key = f"alerts_{stream_id}"
            adaptive_buffer_manager.add_item(buffer_key, alert_data)
            
            # 保留向后兼容的缓冲区（作为备用）
            if stream_id not in self._alerts_buffer:
                self._alerts_buffer[stream_id] = []
            self._alerts_buffer[stream_id].append(alert_data)
            
            # 更新任务告警计数
            for task in self.running_tasks.values():
                if task.stream_id == stream_id and task.status == "running":
                    task.alert_count += 1
                    break
            
            logger.info(f"收到实时告警: 流={stream_id}, 算法={alert_data.get('template_name')}")
            
        except Exception as e:
            logger.error(f"处理告警失败: {e}")
    
    async def _batch_process_results(self):
        """批量处理分析结果和告警 - 优化性能"""
        from config.settings import VideoConfig
        logger.info("实时流结果处理器已启动")
        
        while True:
            try:
                # 使用配置的刷新间隔
                await asyncio.sleep(VideoConfig.STREAM_BUFFER_FLUSH_INTERVAL)
                
                # 处理所有流的缓冲数据
                for stream_id in list(self._frame_results_buffer.keys()):
                    # 检查缓冲区大小，超过阈值立即处理
                    frame_buffer_size = len(self._frame_results_buffer.get(stream_id, []))
                    alerts_buffer_size = len(self._alerts_buffer.get(stream_id, []))
                    
                    if (frame_buffer_size >= VideoConfig.STREAM_BUFFER_BATCH_SIZE or 
                        alerts_buffer_size >= VideoConfig.STREAM_BUFFER_BATCH_SIZE):
                        logger.debug(f"缓冲区大小超过阈值，立即处理: 流={stream_id}, 帧={frame_buffer_size}, 告警={alerts_buffer_size}")
                        await self._flush_buffered_data(stream_id)
                    else:
                        # 定期处理
                        await self._flush_buffered_data(stream_id)
                
            except Exception as e:
                logger.error(f"批量处理结果异常: {e}")
                await asyncio.sleep(5)
    
    async def _adaptive_flush_callback(self, buffer_key: str, items: List[Dict[str, Any]]):
        """自适应缓冲区刷新回调 - 委托给 helpers.buffer_manager"""
        await _adaptive_flush_callback_helper(buffer_key, items, elasticsearch_service)

    async def _flush_buffered_data(self, stream_id: str):
        """刷新指定流的缓冲数据 - 委托给 helpers.buffer_manager"""
        await _flush_buffered_data_helper(
            stream_id, self._frame_results_buffer, self._alerts_buffer, elasticsearch_service
        )

    async def _save_frame_results_to_elasticsearch(self, stream_id: str, frame_results: List[Dict[str, Any]]):
        """保存帧分析结果到Elasticsearch - 委托给 helpers.buffer_manager"""
        await _save_frame_results_helper(stream_id, frame_results, elasticsearch_service)

    async def _save_alerts_to_elasticsearch(self, stream_id: str, alerts: List[Dict[str, Any]]):
        """保存告警到Elasticsearch - 委托给 helpers.buffer_manager"""
        await _save_alerts_helper(stream_id, alerts, elasticsearch_service, self._get_stream_info)
    
    async def _get_stream_info(self, stream_id: str) -> Dict[str, Any]:
        """获取流信息"""
        try:
            # 查找对应的任务
            current_task = None
            for task in self.running_tasks.values():
                if task.stream_id == stream_id:
                    current_task = task
                    break
            
            if current_task:
                return {
                    'name': current_task.stream_name or f'实时流_{stream_id[:8]}',
                    'camera_name': current_task.stream_name or f'摄像头_{stream_id[:8]}', 
                    'location': '实时监控点',
                    'rtsp_url': current_task.rtsp_url,
                }
            else:
                return {
                    'name': f'实时流_{stream_id[:8]}',
                    'camera_name': f'摄像头_{stream_id[:8]}',
                    'location': '未知位置'
                }
        except Exception as e:
            logger.warning(f"获取流信息失败: {e}")
            return {
                'name': f'实时流_{stream_id[:8]}',
                'camera_name': f'摄像头_{stream_id[:8]}',
                'location': '未知位置'
            }
    
    async def _get_stream_template_info(self, stream_id: str, template_id: str) -> Dict[str, Any]:
        """从视频流配置中获取模板信息"""
        try:
            from database.connection import DatabaseManager
            from sqlalchemy import text
            from uuid import UUID
            
            async with DatabaseManager.get_session() as db:
                # 从视频流算法配置表中查询模板名称
                config_query = text("""
                SELECT template_name 
                FROM video_stream_algorithm_configs 
                WHERE stream_id = :stream_id AND template_id = :template_id AND is_active = true
                """)
                config_result = await db.execute(config_query, {
                    'stream_id': UUID(stream_id),
                    'template_id': template_id
                })
                config_row = config_result.fetchone()

                if config_row and config_row[0]:
                    template_name = config_row[0]
                else:
                    # 如果流配置中没有找到，再从算法配置表中查询
                    template_query = text("""
                    SELECT name
                    FROM ai_model_configs
                    WHERE id = :template_id
                    """)
                    template_result = await db.execute(template_query, {'template_id': template_id})
                    template_row = template_result.fetchone()
                    template_name = template_row[0] if template_row else f'未知算法({template_id[:8]})'
                
                # ai_model_configs表没有category字段，使用默认值
                category = 'analysis'  # 默认类别
                
                return {
                    'name': template_name,
                    'category': category
                }
                
        except Exception as e:
            logger.warning(f"获取流模板信息失败: {e}")
            return {
                'name': f'未知算法({template_id[:8]})',
                'category': 'unknown'
            }
    
    async def get_analysis_tasks(self) -> List[Dict[str, Any]]:
        """获取所有分析任务列表"""
        try:
            return [task.to_dict() for task in self.running_tasks.values()]
        except Exception as e:
            logger.error(f"获取分析任务列表失败: {e}")
            return []
    
    async def cleanup_finished_tasks(self, keep_hours: int = 24):
        """清理已完成的任务（保留指定小时数）"""
        try:
            current_time = now()
            tasks_to_remove = []
            
            for task_id, task in self.running_tasks.items():
                if task.status in ['stopped', 'error'] and task.stopped_at:
                    time_diff = current_time - task.stopped_at
                    if time_diff.total_seconds() > keep_hours * 3600:
                        tasks_to_remove.append(task_id)
            
            for task_id in tasks_to_remove:
                del self.running_tasks[task_id]
                logger.info(f"已清理过期任务: {task_id}")
            
            return len(tasks_to_remove)
            
        except Exception as e:
            logger.error(f"清理任务失败: {e}")
            return 0
    
    async def get_buffer_performance_stats(self) -> Dict[str, Any]:
        """获取缓冲区性能统计"""
        try:
            # 获取自适应缓冲区统计
            adaptive_stats = adaptive_buffer_manager.get_performance_stats()
            
            # 获取传统缓冲区统计（向后兼容）
            traditional_stats = {
                "frame_results_buffers": {},
                "alerts_buffers": {}
            }
            
            for stream_id, buffer in self._frame_results_buffer.items():
                traditional_stats["frame_results_buffers"][stream_id] = len(buffer)
            
            for stream_id, buffer in self._alerts_buffer.items():
                traditional_stats["alerts_buffers"][stream_id] = len(buffer)
            
            # 合并统计信息
            return {
                "adaptive_buffer_manager": adaptive_stats,
                "traditional_buffers": traditional_stats,
                "running_tasks_count": len([t for t in self.running_tasks.values() if t.status == "running"]),
                "total_tasks_count": len(self.running_tasks)
            }
            
        except Exception as e:
            logger.error(f"获取缓冲区性能统计失败: {e}")
            return {}
    


# 创建全局实例
stream_analysis_service = StreamAnalysisService()