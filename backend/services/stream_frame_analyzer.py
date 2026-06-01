"""
实时视频流帧分析器
专门用于实时视频流的帧提取和AI分析
基于离线视频分析架构设计，优化实时性能
集成帧质量评估，确保只分析清晰的关键帧
"""

import asyncio
import logging
import cv2
import time
import uuid
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from services.frame_analyzer import FrameAnalyzer
from services.storage import storage_service
from services.ai_analysis_log_service import ai_analysis_log_service
from services.rtsp_connection_manager import RTSPConnectionManager
from services.resilient_ai_analyzer import ResilientAIAnalyzer
from services.composite_detection_service import CompositeDetectionService
from services.helpers.frame_selection_helper import (
    extract_violation_from_ai_response,
    build_alert_data,
    build_composite_alert_data,
    log_successful_analysis,
    log_failed_analysis,
)
from config.settings import PathConfig, VideoConfig
from core.constants import (
    FFMPEG_STREAM_ANALYZE_DURATION, FFMPEG_STREAM_PROBE_SIZE, FFMPEG_MAX_DELAY,
    FFMPEG_FRAME_QUEUE_SIZE, FFMPEG_RECONNECT_INTERVAL, FFMPEG_DEFAULT_FPS,
    STREAM_FRAME_SELECTOR_INTERVAL, STREAM_FRAME_SELECTOR_BUFFER_SIZE,
    STREAM_HEALTH_LOG_INTERVAL, STREAM_QUALITY_STATS_LOG_INTERVAL,
    STREAM_CPU_SLEEP_INTERVAL, AI_RESILIENT_TIMEOUT, AI_RESILIENT_MAX_RETRIES,
)
from utils.timezone_utils import now, BEIJING_TZ
from utils.frame_quality_checker import frame_quality_checker
from utils.frame_buffer import StreamFrameSelector
from utils.ffmpeg_decoder import FFmpegDecoder, FFmpegConfig

logger = logging.getLogger(__name__)


class StreamFrameAnalyzer:
    """实时视频流帧分析器"""

    def __init__(self):
        self.frame_analyzer = FrameAnalyzer()

        # 🔧 关键修复：支持多流并发分析
        # 旧设计：is_analyzing (bool) - 只能分析一个流
        # 新设计：analyzing_streams (dict) - 支持多个流同时分析
        self.analyzing_streams: Dict[str, Dict[str, Any]] = {}  # stream_id -> session_info
        self.rtsp_managers = {}  # stream_id -> RTSPConnectionManager 映射

        # 🔧 进程跟踪：防止ffmpeg进程泄漏
        self.ffmpeg_decoders: Dict[str, FFmpegDecoder] = {}  # stream_id -> FFmpegDecoder

        # 创建具备容错能力的AI分析器
        self.resilient_analyzer = ResilientAIAnalyzer(
            base_analyzer=self.frame_analyzer,
            timeout=AI_RESILIENT_TIMEOUT,
            max_retries=AI_RESILIENT_MAX_RETRIES,
        )

        # 创建复合检测服务（新增）
        self.composite_detection_service = CompositeDetectionService()

    async def _save_frame_image(self, frame_path: str, frame: np.ndarray):
        """保存帧图片"""
        await asyncio.to_thread(cv2.imwrite, frame_path, frame)

    async def start_stream_analysis(self,
                                  rtsp_url: str,
                                  stream_id: str,
                                  templates: List[Dict[str, Any]],
                                  time_configs: Dict[str, Any] = None,
                                  frame_callback: Callable[[Dict[str, Any]], None] = None,
                                  alert_callback: Callable[[Dict[str, Any]], None] = None) -> str:
        """
        启动实时视频流分析

        Args:
            rtsp_url: RTSP流地址
            stream_id: 流ID
            templates: AI分析算法模板列表
            time_configs: 任务时间配置字典 {task_id: time_config}
            frame_callback: 帧分析结果回调函数
            alert_callback: 告警回调函数

        Returns:
            分析会话ID
        """
        try:
            # 🔧 关键修复：检查特定流是否正在分析，而不是全局检查
            if stream_id in self.analyzing_streams:
                existing_session = self.analyzing_streams[stream_id]
                logger.warning(f"⚠️ 流 {stream_id} 已在分析中，会话ID: {existing_session.get('session_id')}")
                raise ValueError(f"流 {stream_id} 已有分析任务正在运行")

            # 创建分析会话
            session_id = f"stream_analysis_{int(time.time())}_{stream_id}"
            session_info = {
                'session_id': session_id,
                'stream_id': stream_id,
                'rtsp_url': rtsp_url,
                'templates': templates,
                'time_configs': time_configs or {},  # 保存时间配置
                'started_at': now(),
                'frame_count': 0,
                'alert_count': 0,
                'status': 'running'
            }

            # 🔧 注册到分析流字典
            self.analyzing_streams[stream_id] = session_info

            # 启动异步分析任务
            asyncio.create_task(self._analyze_stream_continuously(
                rtsp_url, stream_id, templates, time_configs or {}, frame_callback, alert_callback
            ))

            logger.info(f"✅ 实时流分析已启动: 会话={session_id}, 流={stream_id}, 当前活跃流数={len(self.analyzing_streams)}")

            return session_id

        except Exception as e:
            logger.error(f"启动实时流分析失败: {e}")
            # 清理
            if stream_id in self.analyzing_streams:
                del self.analyzing_streams[stream_id]
            raise
    
    async def stop_stream_analysis(self, stream_id: Optional[str] = None) -> bool:
        """
        停止实时视频流分析

        Args:
            stream_id: 流ID。如果为None，停止所有流

        Returns:
            是否成功停止
        """
        try:
            if stream_id:
                # 停止特定流
                if stream_id not in self.analyzing_streams:
                    logger.warning(f"⚠️ 流 {stream_id} 未在分析中")
                    return False

                session_info = self.analyzing_streams[stream_id]
                session_info['status'] = 'stopped'
                session_info['stopped_at'] = now()

                # 🔧 清理FFmpeg解码器
                if stream_id in self.ffmpeg_decoders:
                    decoder = self.ffmpeg_decoders[stream_id]
                    logger.info(f"🧹 停止并清理FFmpeg解码器: 流={stream_id}, PID={decoder.process_pid}")
                    decoder.stop()
                    del self.ffmpeg_decoders[stream_id]

                # 从字典中移除
                del self.analyzing_streams[stream_id]

                logger.info(f"✅ 实时流分析已停止: 流={stream_id}, 剩余活跃流数={len(self.analyzing_streams)}")
                return True
            else:
                # 停止所有流
                if not self.analyzing_streams:
                    logger.warning("⚠️ 没有正在分析的流")
                    return False

                stream_ids = list(self.analyzing_streams.keys())
                for sid in stream_ids:
                    await self.stop_stream_analysis(sid)

                logger.info(f"✅ 所有实时流分析已停止，共停止 {len(stream_ids)} 个流")
                return True

        except Exception as e:
            logger.error(f"停止实时流分析失败: {e}")
            return False
    
    def get_analysis_status(self, stream_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取分析状态

        Args:
            stream_id: 流ID。如果为None，返回所有流的状态

        Returns:
            分析状态信息
        """
        if stream_id:
            # 返回特定流的状态
            if stream_id not in self.analyzing_streams:
                return None
            return {
                **self.analyzing_streams[stream_id],
                'is_analyzing': True
            }
        else:
            # 返回所有流的状态
            return {
                'total_streams': len(self.analyzing_streams),
                'streams': {
                    sid: {**info, 'is_analyzing': True}
                    for sid, info in self.analyzing_streams.items()
                }
            }
    
    async def _analyze_stream_continuously(self,
                                         rtsp_url: str,
                                         stream_id: str,
                                         templates: List[Dict[str, Any]],
                                         time_configs: Dict[str, Any],
                                         frame_callback: Callable,
                                         alert_callback: Callable):
        """持续分析视频流 - 使用FFmpeg专业解码器"""
        ffmpeg_decoder = None
        try:
            # ✨ 创建FFmpeg专业解码器配置
            ffmpeg_config = FFmpegConfig(
                rtsp_transport="tcp",  # TCP传输更稳定
                skip_frame="nokey" if VideoConfig.FFMPEG_ONLY_KEYFRAMES else "none",  # 只解码I帧
                analyzeduration=FFMPEG_STREAM_ANALYZE_DURATION,
                probesize=FFMPEG_STREAM_PROBE_SIZE,
                max_delay=FFMPEG_MAX_DELAY,
            )

            logger.info(
                f"🚀 启动FFmpeg专业解码器: "
                f"传输协议={ffmpeg_config.rtsp_transport}, "
                f"跳帧策略={ffmpeg_config.skip_frame}, "
                f"只解I帧={'是' if VideoConfig.FFMPEG_ONLY_KEYFRAMES else '否'}"
            )

            # ✨ 创建FFmpeg解码器
            ffmpeg_decoder = FFmpegDecoder(
                rtsp_url=rtsp_url,
                config=ffmpeg_config,
                frame_queue_size=FFMPEG_FRAME_QUEUE_SIZE,
                reconnect_interval=FFMPEG_RECONNECT_INTERVAL,
            )

            # 🔧 注册到解码器字典（防止重复启动和进程泄漏）
            if stream_id in self.ffmpeg_decoders:
                logger.warning(f"⚠️ 流 {stream_id} 已存在FFmpeg解码器，先清理")
                old_decoder = self.ffmpeg_decoders[stream_id]
                old_decoder.stop()
            self.ffmpeg_decoders[stream_id] = ffmpeg_decoder

            # 启动解码器（放入线程，避免阻塞事件循环）
            started = await asyncio.to_thread(ffmpeg_decoder.start)
            if not started:
                raise ValueError(f"无法启动FFmpeg解码器: {rtsp_url}")

            # 获取帧率信息
            fps = ffmpeg_decoder.fps
            if fps <= 0:
                fps = FFMPEG_DEFAULT_FPS

            # 计算抽帧间隔（使用配置的间隔秒数，优化实时性能）
            frame_interval = max(1, int(fps * VideoConfig.STREAM_FRAME_INTERVAL))

            # 🆕 创建帧质量选择器（企业级质量保证）
            frame_selector = StreamFrameSelector(
                selection_interval=STREAM_FRAME_SELECTOR_INTERVAL,
                buffer_size=STREAM_FRAME_SELECTOR_BUFFER_SIZE,
                min_quality_score=VideoConfig.FRAME_QUALITY_MIN_SCORE,
            )

            logger.info(
                f"🎯 实时流分析启动: FPS={fps}, "
                f"抽帧间隔={frame_interval}, "
                f"质量过滤已启用(最低分数={VideoConfig.FRAME_QUALITY_MIN_SCORE}, "
                f"最低清晰度={VideoConfig.FRAME_SHARPNESS_MIN}, 严格模式=True)"
            )

            # 创建临时目录
            temp_dir = Path(PathConfig.TEMP_DIR) / f"stream_{stream_id}"
            temp_dir.mkdir(parents=True, exist_ok=True)

            frame_count = 0
            last_analysis_time = 0
            warmup_frames_discarded = 0  # ✨ 预热丢弃计数
            quality_frames_added = 0     # ✨ 加入质量缓冲区的帧数
            quality_frames_rejected = 0  # ✨ 质量过滤拒绝的帧数

            # 🔧 修复：检查特定流是否应继续分析
            while stream_id in self.analyzing_streams:
                # ✨ 使用FFmpeg解码器读取帧
                ret, frame = await asyncio.to_thread(ffmpeg_decoder.read, timeout=2.0)

                if not ret or frame is None:
                    # 检查解码器是否存活
                    if not ffmpeg_decoder.is_alive():
                        logger.error(f"✗ FFmpeg解码器已停止，无法恢复，停止分析: {stream_id}")
                        break
                    # 超时，跳过本次
                    await asyncio.sleep(0.1)
                    continue

                frame_count += 1
                current_time = time.time()

                # 🆕 预热期：丢弃前N帧（解码器启动时的不稳定帧）
                if warmup_frames_discarded < VideoConfig.FRAME_WARMUP_COUNT:
                    warmup_frames_discarded += 1
                    if warmup_frames_discarded == 1:
                        logger.info(
                            f"🔥 开始预热期：丢弃前{VideoConfig.FRAME_WARMUP_COUNT}帧（FFmpeg解码器初始化）"
                        )
                    if warmup_frames_discarded == VideoConfig.FRAME_WARMUP_COUNT:
                        logger.info(f"✅ 预热完成：已丢弃{VideoConfig.FRAME_WARMUP_COUNT}帧，开始正常处理")
                    continue  # 跳过预热帧

                # 定期检查解码器健康度
                if frame_count % STREAM_HEALTH_LOG_INTERVAL == 0:
                    stats = ffmpeg_decoder.get_stats()
                    logger.info(
                        f"📊 FFmpeg解码器状态: {'运行中' if stats['is_running'] else '已停止'} "
                        f"(解码帧数: {stats['total_frames_decoded']}, "
                        f"丢帧数: {stats['total_frames_dropped']}, "
                        f"队列: {stats['queue_size']}, "
                        f"FPS: {stats['fps']}, "
                        f"分辨率: {stats['resolution']})"
                    )

                # 🆕 先将帧添加到质量选择器
                best_frame = frame_selector.process_frame(frame, frame_count, current_time)

                # 🆕 只有当选择器返回高质量帧时才进行AI分析
                # 检查是否需要分析这一帧
                if best_frame and (frame_count % frame_interval == 0 or (current_time - last_analysis_time) >= 10):
                    # 在抽帧和AI分析之前,先检查时间配置
                    from utils.time_config_checker import check_should_run_now

                    # 检查所有任务的时间配置,只要有一个任务在时间范围内就处理帧
                    should_process_frame = False
                    allowed_templates = []

                    for template in templates:
                        task_id = template.get('task_id')
                        if not task_id:
                            # 没有task_id的模板默认允许运行
                            allowed_templates.append(template)
                            should_process_frame = True
                            continue

                        time_config = time_configs.get(task_id)
                        should_run, reason = check_should_run_now(time_config)

                        if should_run:
                            allowed_templates.append(template)
                            should_process_frame = True
                        else:
                            # 每5分钟记录一次跳过信息(避免日志过多)
                            if frame_count % (frame_interval * 300) == 0:  # 约5分钟
                                logger.info(f"⏸️ 任务 {template.get('name', task_id)} 不在运行时间内,跳过处理: {reason}")

                    if should_process_frame and allowed_templates:
                        last_analysis_time = current_time

                        # 🆕 使用高质量帧进行分析
                        logger.info(
                            f"✨ 使用高质量帧进行AI分析: "
                            f"帧{best_frame.frame_index}, "
                            f"质量分数={best_frame.quality_metrics.quality_score:.2f}, "
                            f"清晰度={best_frame.quality_metrics.sharpness:.2f}"
                        )

                        # 异步分析帧(只处理允许运行的模板，使用高质量帧)
                        asyncio.create_task(self._analyze_frame_async(
                            best_frame.frame, best_frame.frame_index, best_frame.timestamp,
                            stream_id, allowed_templates,
                            temp_dir, frame_callback, alert_callback
                        ))

                        # 更新会话统计
                        if stream_id in self.analyzing_streams:
                            self.analyzing_streams[stream_id]['frame_count'] = frame_count
                    # 如果没有任何任务在时间范围内,不处理帧(不抽帧、不上传MinIO、不调用AI)

                # 定期输出质量过滤统计
                if frame_count % STREAM_QUALITY_STATS_LOG_INTERVAL == 0:
                    stats = frame_selector.get_statistics()
                    logger.info(
                        f"📊 帧质量过滤统计[帧{frame_count}]: "
                        f"接收={stats['total_received']} | "
                        f"过滤={stats['total_filtered']}({stats['filter_rate']}) | "
                        f"选中={stats['total_selected']}({stats['select_rate']}) | "
                        f"缓冲区={stats['buffer_size']}/{stats['buffer_capacity']}"
                    )

                # 短暂延迟以避免过度占用CPU
                await asyncio.sleep(STREAM_CPU_SLEEP_INTERVAL)
        
        except Exception as e:
            logger.error(f"实时流分析异常: {e}")
            if stream_id in self.analyzing_streams:
                self.analyzing_streams[stream_id]['status'] = 'error'
                self.analyzing_streams[stream_id]['error'] = str(e)

        finally:
            # ✨ 清理FFmpeg解码器
            if ffmpeg_decoder:
                ffmpeg_decoder.stop()
                stats = ffmpeg_decoder.get_stats()
                logger.info(
                    f"📊 FFmpeg解码器统计 [{stream_id}]: "
                    f"总解码帧数={stats['total_frames_decoded']}, "
                    f"总丢帧数={stats['total_frames_dropped']}, "
                    f"分辨率={stats['resolution']}, "
                    f"FPS={stats['fps']}"
                )

            # 🔧 从解码器字典中移除
            if stream_id in self.ffmpeg_decoders:
                del self.ffmpeg_decoders[stream_id]
                logger.info(f"🧹 已从解码器字典移除: 流={stream_id}")

            # 🔧 从分析流字典中移除
            if stream_id in self.analyzing_streams:
                del self.analyzing_streams[stream_id]
                logger.info(f"🧹 已从分析流字典移除: 流={stream_id}, 剩余活跃流数={len(self.analyzing_streams)}")

            # 清理临时文件
            try:
                import shutil
                temp_dir = Path(PathConfig.TEMP_DIR) / f"stream_{stream_id}"
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"已清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时文件失败: {e}")
    
    async def _analyze_frame_async(self,
                                 frame: np.ndarray,
                                 frame_index: int,
                                 timestamp: float,
                                 stream_id: str,
                                 templates: List[Dict[str, Any]],
                                 temp_dir: Path,
                                 frame_callback: Callable,
                                 alert_callback: Callable):
        """异步分析单帧"""
        try:
            # 保存帧图片
            frame_filename = f"stream_frame_{frame_index:06d}.jpg"
            frame_path = temp_dir / frame_filename

            # 保存图片
            await self._save_frame_image(str(frame_path), frame)
            
            # 上传帧图片到MinIO
            minio_url = await storage_service.upload_stream_frame_image(
                str(frame_path), stream_id, frame_index
            )
            
            # 创建并发分析任务列表，根据detection_capabilities判断模式
            analysis_tasks = []
            for template in templates:
                # 检查是否有检测能力配置（复合检测）
                detection_capabilities = template.get('detection_capabilities', [])

                if detection_capabilities and len(detection_capabilities) > 1:
                    # 复合检测模式：该算法支持多种检测类型
                    logger.debug(
                        f"算法 {template['name']} 使用复合检测模式，"
                        f"检测类型: {detection_capabilities}, 帧{frame_index}"
                    )
                    task = asyncio.create_task(
                        self._analyze_composite_detection_single(
                            frame_path, frame_index, timestamp, stream_id,
                            template, detection_capabilities, minio_url, alert_callback
                        )
                    )
                    analysis_tasks.append(task)
                else:
                    # 传统单检测模式（向后兼容）
                    logger.debug(f"算法 {template['name']} 使用单检测模式，帧{frame_index}")
                    task = asyncio.create_task(
                        self._analyze_single_template(
                            frame_path, frame_index, timestamp, stream_id, template,
                            minio_url, alert_callback
                        )
                    )
                    analysis_tasks.append(task)

            # 并发执行所有算法分析
            logger.debug(f"开始并发分析 {len(templates)} 个算法: 帧{frame_index}")
            analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
            
            # 处理分析结果和异常
            successful_results = []
            for i, result in enumerate(analysis_results):
                if isinstance(result, Exception):
                    logger.error(f"算法{templates[i]['name']}分析失败: {result}")
                    # 记录失败的AI调用日志
                    await self._log_failed_analysis(
                        templates[i], frame_index, timestamp, stream_id, 
                        str(frame_path), str(result)
                    )
                else:
                    successful_results.append(result)
            
            analysis_results = successful_results
            
            # 执行帧分析结果回调
            if analysis_results and frame_callback:
                try:
                    for result in analysis_results:
                        frame_callback(result)
                except Exception as callback_error:
                    logger.error(f"帧分析回调执行失败: {callback_error}")
            
            # 清理本地临时图片文件
            try:
                frame_path.unlink()
            except Exception as cleanup_error:
                logger.warning(f"清理帧图片失败: {cleanup_error}")
        
        except Exception as e:
            logger.error(f"异步分析帧失败: 帧{frame_index}, 错误={e}")
    
    async def _analyze_composite_detection_single(self,
                                                frame_path: Path,
                                                frame_index: int,
                                                timestamp: float,
                                                stream_id: str,
                                                template: Dict[str, Any],
                                                detection_capabilities: List[str],
                                                minio_url: str,
                                                alert_callback: Callable) -> Dict[str, Any]:
        """
        复合检测模式：一次AI调用检测多种违规类型

        Args:
            frame_path: 帧图片路径
            frame_index: 帧索引
            timestamp: 时间戳
            stream_id: 视频流ID
            template: 算法模板配置
            detection_capabilities: 检测能力列表 ['safety_helmet', 'smoking', ...]
            minio_url: MinIO图片URL
            alert_callback: 告警回调函数
        """
        try:
            start_time = time.time()
            model_config_id = template.get('id')

            logger.info(
                f"🔍 复合检测开始: 算法={template['name']}, "
                f"检测类型={detection_capabilities}, 帧{frame_index}"
            )

            # 构建template_configs用于复合检测服务
            from services.video_analysis_template_service import video_analysis_template_service

            template_configs = []
            for type_code in detection_capabilities:
                # 从detection_type_templates获取详细信息
                type_template = await video_analysis_template_service.get_detection_type_by_code(type_code)
                if type_template:
                    display_name = type_template.get('display_name', type_code)
                    logger.info(f"🔍 加载检测类型: {type_code} -> {display_name}")  # 调试日志
                    template_configs.append({
                        'detection_type_code': type_code,
                        'display_name': display_name,  # 🔧 修复：使用display_name字段（与数据库字段一致）
                        'category': type_template.get('category', 'unknown'),
                        'severity': type_template.get('severity', 'medium')
                    })

            if not template_configs:
                logger.warning(f"未能加载检测类型模板，降级为单检测模式")
                return await self._analyze_single_template(
                    frame_path, frame_index, timestamp, stream_id,
                    template, minio_url, alert_callback
                )

            # 调用复合检测服务
            # 🔧 修复：始终使用本地路径，让unified_ai_client根据模型类型决定：
            #   - 本地模型（vLLM）：转换为MinIO内网URL
            #   - 公网模型（lanyi、qwen等）：下载并转base64编码
            final_image_path = str(frame_path)

            composite_result = await self.composite_detection_service.analyze_frame_composite(
                image_path=final_image_path,
                template_configs=template_configs,
                model_config_id=model_config_id
            )

            response_time_ms = int((time.time() - start_time) * 1000)

            # 检查是否有任何违规
            violations = composite_result.get('violations', [])
            has_alert = any(v.get('has_violation', False) for v in violations)

            # 构建北京时间
            datetime_beijing = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ).replace(tzinfo=None)

            # 构建帧分析结果
            frame_result = {
                'task_id': template.get('task_id', f"unknown_task_{template['id']}"),
                'stream_id': stream_id,
                'frame_index': frame_index,
                'timestamp': timestamp,
                'datetime': datetime_beijing.isoformat(),
                'template_id': template['id'],
                'template_name': template['name'],
                'category': template['category'],
                'priority': template.get('priority', 1),
                'has_alert': has_alert,
                'image_url': minio_url,
                'detection_mode': 'composite',  # 标记为复合检测
                'violations': violations,  # 包含所有违规类型的结果
                'detection_summary': composite_result.get('detection_summary', {}),
                'ai_response': composite_result.get('raw_response', ''),
                'model_used': composite_result.get('model_used', ''),
                'model': composite_result.get('model_used', ''),  # ✅ 添加model字段（日志需要）
                'provider': composite_result.get('provider', ''),  # ✅ 添加provider字段
                'model_config_id': composite_result.get('model_config_id', ''),  # ✅ 添加model_config_id
                'response_time': composite_result.get('response_time', response_time_ms / 1000),
                # ✅ 传递完整的API调用详情
                'api_call_details': composite_result.get('api_call_details', {}),
                'prompt_used': composite_result.get('prompt_used', '')
            }

            logger.info(
                f"✅ 复合检测完成: 帧{frame_index}, "
                f"检测{len(violations)}种类型, 发现违规{len([v for v in violations if v.get('has_violation')])}项"
            )

            # 记录成功的AI调用日志
            if VideoConfig.ENABLE_STREAM_AI_LOGGING:
                await self._log_successful_analysis(
                    template, frame_index, timestamp, stream_id,
                    str(frame_path), composite_result, response_time_ms
                )

            # 如果有告警，为每个违规类型执行告警回调
            if has_alert and alert_callback:
                for violation in violations:
                    if violation.get('has_violation'):
                        await self._handle_composite_alert_callback(
                            template, frame_index, timestamp, stream_id,
                            violation, minio_url, alert_callback, response_time_ms
                        )

            return frame_result

        except Exception as e:
            logger.error(f"❌ 复合检测失败: {e}, 帧{frame_index}")
            # 记录失败日志
            await self._log_failed_analysis(
                template, frame_index, timestamp, stream_id,
                str(frame_path), str(e)
            )
            raise

    async def _analyze_single_template(self,
                                      frame_path: Path,
                                      frame_index: int,
                                      timestamp: float,
                                      stream_id: str,
                                      template: Dict[str, Any],
                                      minio_url: str,
                                      alert_callback: Callable) -> Dict[str, Any]:
        """分析单个算法模板（并发执行）"""
        try:
            start_time = time.time()
            
            # AI分析 - 从模板获取模型配置ID
            # ✅ 修复：使用正确的字段名'id'（不是'template_id'）
            model_config_id = template.get('id')

            # 如果模板没有关联AI模型配置，尝试从数据库获取活跃的AI模型配置
            if not model_config_id:
                from services.ai_config_manager import ai_config_manager
                configs = await ai_config_manager.get_all_active_configs()
                if configs:
                    # 优先使用GPT模型，其次是其他模型
                    for config_id, config in configs.items():
                        if config['provider'].lower() in ['gpt', 'openai']:
                            model_config_id = config_id
                            logger.info(f"流分析使用数据库中的GPT模型配置: {config['name']}")
                            break
                    # 如果没有GPT，使用第一个可用的模型
                    if not model_config_id:
                        model_config_id = list(configs.keys())[0]
                        config = configs[model_config_id]
                        logger.info(f"流分析使用数据库中的默认模型配置: {config['name']} ({config['provider']})")
            
            # 使用带超时和重试的AI分析
            analysis_result = await self.resilient_analyzer.analyze_with_timeout_retry(
                image_path=str(frame_path),
                prompt=template['prompt_content'],
                model_config_id=model_config_id
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # 解析违规信息
            has_alert = self._extract_violation_from_ai_response(
                analysis_result.get('ai_response', '')
            )
            
            # 构建帧分析结果
            # ⚠️ timestamp是UTC Unix时间戳（标准），datetime需要明确转换为北京时间
            datetime_beijing = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ).replace(tzinfo=None)

            frame_result = {
                'task_id': template.get('task_id', f"unknown_task_{template['id']}"),  # 从template中获取task_id
                'stream_id': stream_id,
                'frame_index': frame_index,
                'timestamp': timestamp,  # UTC Unix时间戳
                'datetime': datetime_beijing.isoformat(),  # 北京时间ISO格式
                'template_id': template['id'],
                'template_name': template['name'],
                'category': template['category'],
                'priority': template.get('priority', 1),
                'has_alert': has_alert,
                'image_url': minio_url,
                **analysis_result
            }
            
            # 记录成功的AI调用日志（可配置）
            if VideoConfig.ENABLE_STREAM_AI_LOGGING:
                await self._log_successful_analysis(
                    template, frame_index, timestamp, stream_id, 
                    str(frame_path), analysis_result, response_time_ms
                )
            
            # 如果有告警，执行告警回调
            if has_alert and alert_callback:
                await self._handle_alert_callback(
                    template, frame_index, timestamp, stream_id,
                    analysis_result, minio_url, alert_callback, response_time_ms
                )
            
            logger.debug(f"流帧分析完成: 帧{frame_index}, 算法={template['name']}, 告警={has_alert}")
            return frame_result
            
        except Exception as e:
            logger.error(f"❌ 算法{template['name']}分析失败(已重试): {e}")

            # 返回降级结果 - 不抛出异常,避免影响其他算法
            # ⚠️ timestamp是UTC Unix时间戳（标准），datetime需要明确转换为北京时间
            datetime_beijing_fallback = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ).replace(tzinfo=None)

            return {
                'task_id': template.get('task_id', f"unknown_task_{template['id']}"),
                'stream_id': stream_id,
                'frame_index': frame_index,
                'timestamp': timestamp,  # UTC Unix时间戳
                'datetime': datetime_beijing_fallback.isoformat(),  # 北京时间ISO格式
                'template_id': template['id'],
                'template_name': template['name'],
                'category': template['category'],
                'priority': template.get('priority', 1),
                'has_alert': False,
                'image_url': '',
                'error': str(e),
                'degraded': True,  # 标记为降级模式
                'ai_response': f'AI分析失败: {str(e)}',
                'confidence': 0.0
            }
    
    async def _log_successful_analysis(self, template: Dict[str, Any], frame_index: int,
                                     timestamp: float, stream_id: str, frame_path: str,
                                     analysis_result: Dict[str, Any], response_time_ms: int):
        """记录成功的AI调用日志 - 委托给 helpers.frame_selection_helper"""
        rtsp_url = self.analyzing_streams.get(stream_id, {}).get('rtsp_url', '')
        await log_successful_analysis(
            template, frame_index, timestamp, stream_id,
            frame_path, analysis_result, response_time_ms, rtsp_url
        )

    async def _log_failed_analysis(self, template: Dict[str, Any], frame_index: int,
                                 timestamp: float, stream_id: str, frame_path: str,
                                 error_message: str):
        """记录失败的AI调用日志 - 委托给 helpers.frame_selection_helper"""
        rtsp_url = self.analyzing_streams.get(stream_id, {}).get('rtsp_url', '')
        await log_failed_analysis(
            template, frame_index, timestamp, stream_id,
            frame_path, error_message, rtsp_url
        )

    async def _handle_alert_callback(self, template: Dict[str, Any], frame_index: int,
                                   timestamp: float, stream_id: str, analysis_result: Dict[str, Any],
                                   minio_url: str, alert_callback: Callable, response_time_ms: int):
        """处理告警回调 - 委托给 helpers.frame_selection_helper"""
        try:
            alert_data = build_alert_data(
                template, frame_index, timestamp, stream_id,
                analysis_result, minio_url, response_time_ms
            )
            alert_callback(alert_data)

            # 更新会话告警计数
            if stream_id in self.analyzing_streams:
                self.analyzing_streams[stream_id]['alert_count'] += 1

        except Exception as callback_error:
            logger.error(f"告警回调执行失败: {callback_error}")

    async def _handle_composite_alert_callback(self,
                                              template: Dict[str, Any],
                                              frame_index: int,
                                              timestamp: float,
                                              stream_id: str,
                                              violation: Dict[str, Any],
                                              minio_url: str,
                                              alert_callback: Callable,
                                              response_time_ms: int):
        """处理复合检测告警回调 - 委托给 helpers.frame_selection_helper"""
        try:
            alert_data = build_composite_alert_data(
                template, frame_index, timestamp, stream_id,
                violation, minio_url, response_time_ms
            )
            alert_callback(alert_data)

            # 更新会话告警计数
            if stream_id in self.analyzing_streams:
                self.analyzing_streams[stream_id]['alert_count'] += 1

        except Exception as callback_error:
            logger.error(f"复合检测告警回调执行失败: {callback_error}")

    def _extract_violation_from_ai_response(self, ai_response: str) -> bool:
        """从AI多模态响应中提取违规信息 - 委托给 helpers.frame_selection_helper"""
        return extract_violation_from_ai_response(ai_response)
    


# 创建全局实例
stream_frame_analyzer = StreamFrameAnalyzer()
