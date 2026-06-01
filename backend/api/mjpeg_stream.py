"""
企业级MJPEG流媒体服务
用于替代复杂的WebRTC方案，提供稳定的实时视频流
添加帧完整性检查，确保推送有效帧
"""

import asyncio
import cv2
import logging
import time
from typing import Optional, Dict, Set
from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse
import threading
from queue import Queue, Empty
import uuid
import numpy as np
from utils.frame_quality_checker import frame_quality_checker
from services.helpers.mjpeg_frame_processor import (
    clear_opencv_buffer,
    is_frame_valid as _is_frame_valid_helper,
    try_connect_rtsp,
)
from core.constants import (
    MJPEG_FPS_TARGET, MJPEG_FRAME_QUEUE_SIZE, MJPEG_JPEG_QUALITY,
    MJPEG_CLEANUP_INTERVAL, MJPEG_FRAME_MEMORY_LIMIT, MJPEG_RECONNECT_WARMUP_FRAMES,
    MJPEG_BUFFER_CLEAR_INTERVAL, MJPEG_NO_FRAME_SLEEP,
    MJPEG_LOG_INTERVAL, MJPEG_STATUS_LOG_INTERVAL, MJPEG_QUALITY_CHECK_INTERVAL,
    MJPEG_STRICT_MODE_WARMUP_LIMIT,
    FRAME_SIZE_MISMATCH_TOLERANCE,
    OPENCV_UDP_ANALYZE_DURATION, OPENCV_UDP_PROBE_SIZE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mjpeg", tags=["MJPEG流媒体"])

# 全局流管理器
class MJPEGStreamManager:
    def __init__(self):
        self.streams: Dict[str, 'StreamProcessor'] = {}
        self.clients: Dict[str, Set[str]] = {}  # stream_id -> client_ids
        self.tasks: Dict[str, asyncio.Task] = {}  # stream_id -> processing_task

    def get_or_create_stream(self, rtsp_url: str) -> str:
        """获取或创建RTSP流处理器"""
        stream_id = f"mjpeg_{hash(rtsp_url)}"

        if stream_id not in self.streams:
            processor = StreamProcessor(rtsp_url, stream_id)
            self.streams[stream_id] = processor
            self.clients[stream_id] = set()

            # 🔧 ARM兼容：使用asyncio.to_thread替代ThreadPoolExecutor
            task = asyncio.create_task(asyncio.to_thread(processor.start_processing))
            self.tasks[stream_id] = task
            logger.info(f"✅ 创建新的MJPEG流: {stream_id} for {rtsp_url[:50]}...")

        return stream_id

    def add_client(self, stream_id: str, client_id: str):
        """添加客户端"""
        if stream_id in self.clients:
            self.clients[stream_id].add(client_id)
            logger.debug(f"📺 客户端 {client_id} 连接到流 {stream_id}")

    def remove_client(self, stream_id: str, client_id: str):
        """移除客户端"""
        if stream_id in self.clients:
            self.clients[stream_id].discard(client_id)
            logger.debug(f"📺 客户端 {client_id} 断开流 {stream_id}")

            # 如果没有客户端了，停止流
            if len(self.clients[stream_id]) == 0:
                self.stop_stream(stream_id)

    def stop_stream(self, stream_id: str):
        """停止流处理"""
        if stream_id in self.streams:
            self.streams[stream_id].stop()
            del self.streams[stream_id]
            del self.clients[stream_id]

            # 取消异步任务
            if stream_id in self.tasks:
                self.tasks[stream_id].cancel()
                del self.tasks[stream_id]

            logger.info(f"🛑 停止MJPEG流: {stream_id}")

    def get_frame(self, stream_id: str) -> Optional[bytes]:
        """获取最新帧"""
        if stream_id in self.streams:
            return self.streams[stream_id].get_latest_frame()
        return None

class StreamProcessor:
    def __init__(self, rtsp_url: str, stream_id: str):
        self.rtsp_url = rtsp_url
        self.stream_id = stream_id
        self.latest_frame: Optional[bytes] = None
        self.running = False
        self.frame_queue = Queue(maxsize=MJPEG_FRAME_QUEUE_SIZE)
        self.last_frame_time = 0
        self.fps_target = MJPEG_FPS_TARGET
        self._lock = threading.Lock()
        self._cap_lock = threading.Lock()
        self._last_cleanup_time = time.time()
        self._cleanup_interval = MJPEG_CLEANUP_INTERVAL
        self._frame_memory_limit = MJPEG_FRAME_MEMORY_LIMIT

        # 🆕 帧完整性统计
        self._total_frames_received = 0
        self._invalid_frames_filtered = 0
        self._last_valid_frame = None  # 保存最后一个有效帧，用于填充

        # 🆕 帧质量过滤统计
        self._total_quality_checked = 0
        self._low_quality_frames_filtered = 0

        # 🆕 重连预热机制（平衡稳定性和流畅度）
        self._reconnect_warmup_frames = MJPEG_RECONNECT_WARMUP_FRAMES
        self._current_warmup_count = 0  # 当前预热计数
        self._is_warming_up = False  # 是否在预热期

        # 🆕 帧尺寸一致性检查
        self._expected_frame_size = None  # (width, height)
        self._frame_size_mismatch_count = 0  # 尺寸不匹配计数

    def _clear_buffer(self, cap: cv2.VideoCapture) -> None:
        """清空OpenCV缓冲区 - 委托给 helpers.mjpeg_frame_processor"""
        clear_opencv_buffer(cap)

    def _is_frame_valid(self, frame: np.ndarray, strict: bool = False) -> bool:
        """帧完整性检查 - 委托给 helpers.mjpeg_frame_processor（保留帧尺寸一致性状态）"""
        # 帧尺寸一致性检查（需要维护实例状态，不完全委托）
        if frame is not None and frame.size > 0 and len(frame.shape) == 3:
            height, width = frame.shape[:2]
            if self._expected_frame_size is None:
                self._expected_frame_size = (width, height)
                logger.debug(f"设置期望帧尺寸: {width}x{height}")
            elif (width, height) != self._expected_frame_size:
                self._frame_size_mismatch_count += 1
                logger.warning(
                    f"帧尺寸不匹配: 期望{self._expected_frame_size}, "
                    f"实际{width}x{height}, 计数={self._frame_size_mismatch_count}"
                )
                if self._frame_size_mismatch_count > FRAME_SIZE_MISMATCH_TOLERANCE:
                    logger.info(f"更新期望帧尺寸: {width}x{height}")
                    self._expected_frame_size = (width, height)
                    self._frame_size_mismatch_count = 0
                return False
            else:
                self._frame_size_mismatch_count = 0

        # 委托核心帧质量检查给helper
        is_valid, _, _ = _is_frame_valid_helper(frame, strict, self._expected_frame_size)
        return is_valid

    def start_processing(self):
        """开始处理RTSP流"""
        self.running = True
        cap = None

        try:
            # 设置OpenCV日志级别，屏蔽FFmpeg H264解码警告
            try:
                # 尝试设置OpenCV日志级别（不同版本的OpenCV常量可能不同）
                if hasattr(cv2, 'LOG_LEVEL_ERROR'):
                    cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
                elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
                    cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
                else:
                    # 使用数字值：0=SILENT, 1=FATAL, 2=ERROR, 3=WARN, 4=INFO, 5=DEBUG
                    cv2.setLogLevel(2)  # ERROR级别
            except Exception as cv_log_error:
                logger.warning(f"无法设置OpenCV日志级别: {cv_log_error}")
            
            logger.info(f"🎬 开始创建VideoCapture对象: {self.rtsp_url}")
            
            # 根据ffprobe分析，这个流需要特殊参数
            # H264流，pixel format未指定，需要增加分析时间
            
            # 多策略尝试连接 - 委托给 helpers.mjpeg_frame_processor
            cap = try_connect_rtsp(self.rtsp_url)

            if not cap:
                logger.error(f"所有连接策略都失败了")
                return

            # 详细检查OpenCV连接状态
            is_opened = cap.isOpened()
            logger.info(f"🔍 VideoCapture状态检查: isOpened={is_opened}")

            if not is_opened:
                logger.error(f"❌ 无法打开RTSP流: {self.rtsp_url}")
                # 尝试获取更多诊断信息
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.error(f"📊 OpenCV诊断信息 - FPS: {fps}, 宽度: {width}, 高度: {height}")
                return

            # 获取流属性信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            logger.info(f"📊 RTSP流属性 - FPS: {fps}, 分辨率: {width}x{height}")
            logger.info(f"✅ 开始处理MJPEG流: {self.stream_id}")

            frame_interval = 1.0 / self.fps_target
            frame_count = 0
            last_buffer_clear_time = time.time()  # 上次清空缓冲区的时间

            while self.running:
                current_time = time.time()

                # 定期清空缓冲区，避免累积延迟
                if current_time - last_buffer_clear_time > MJPEG_BUFFER_CLEAR_INTERVAL:
                    logger.debug(f"🔄 定期清空缓冲区，避免延迟累积")
                    self._clear_buffer(cap)
                    last_buffer_clear_time = current_time

                # 控制帧率
                # NOTE(async): time.sleep 在此处合理 — start_processing 运行在独立线程中（通过 asyncio.to_thread），不会阻塞事件循环
                if current_time - self.last_frame_time < frame_interval:
                    time.sleep(0.01)
                    continue

                if frame_count % MJPEG_LOG_INTERVAL == 0:
                    logger.info(f"🎞️ 尝试读取第{frame_count + 1}帧...")

                # 🆕 优化读取策略：先grab再retrieve，避免阻塞
                # grab()只从缓冲区抓取，不解码，更快
                # retrieve()才真正解码
                grabbed = cap.grab()
                if not grabbed:
                    logger.warning(f"⚠️ grab()失败: {self.stream_id}")
                    ret, frame = False, None
                else:
                    ret, frame = cap.retrieve()

                if not ret or frame is None:
                    logger.warning(f"⚠️ 读取帧失败: {self.stream_id} (第{frame_count + 1}帧)")

                    # 检查连接状态
                    if not cap.isOpened():
                        logger.error(f"❌ VideoCapture连接已断开: {self.stream_id}")

                    # 释放旧连接
                    try:
                        cap.release()
                    except Exception as release_error:
                        logger.warning(f"⚠️ 释放VideoCapture时出错: {release_error}")

                    # NOTE(async): time.sleep 在此处合理 — 运行在独立线程中（asyncio.to_thread）
                    time.sleep(1)

                    # 🆕 尝试重连（使用成功的连接策略）
                    logger.info(f"🔄 尝试重新连接RTSP流: {self.stream_id}")

                    # 使用与初始连接相同的策略
                    import os
                    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = f'rtsp_transport;udp|analyzeduration;{OPENCV_UDP_ANALYZE_DURATION}|probesize;{OPENCV_UDP_PROBE_SIZE}'

                    cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    # 重新设置优化参数
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # 与初始设置一致
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 25000)
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 20000)
                    cap.set(cv2.CAP_PROP_FPS, MJPEG_FPS_TARGET)

                    if cap.isOpened():
                        logger.info(f"✅ RTSP流重连成功: {self.stream_id}")

                        # 🆕 关键优化：清空旧缓冲区
                        self._clear_buffer(cap)

                        # 🆕 进入预热期（跳过重连后的脏帧）
                        self._is_warming_up = True
                        self._current_warmup_count = 0
                        # 重置帧尺寸期望（重连后可能变化）
                        self._expected_frame_size = None
                        self._frame_size_mismatch_count = 0
                        logger.info(f"🔥 进入预热期，将跳过前{self._reconnect_warmup_frames}帧")

                        # 不再立即处理第一帧，而是continue让循环跳过预热帧
                        continue
                    else:
                        logger.error(f"❌ RTSP流重连失败: {self.stream_id}")
                        # NOTE(async): time.sleep 在此处合理 — 运行在独立线程中（asyncio.to_thread）
                        time.sleep(5)  # 重连失败时等待更长时间
                        continue

                frame_count += 1
                self._total_frames_received += 1
                if frame_count % MJPEG_LOG_INTERVAL == 0:
                    logger.info(f"✅ 成功读取第{frame_count}帧，尺寸: {frame.shape if frame is not None else 'None'}")

                # 🆕 预热期处理：跳过重连后的前N帧
                if self._is_warming_up:
                    self._current_warmup_count += 1
                    logger.debug(f"🔥 预热期：跳过第{self._current_warmup_count}/{self._reconnect_warmup_frames}帧")

                    if self._current_warmup_count >= self._reconnect_warmup_frames:
                        self._is_warming_up = False
                        logger.info(f"✅ 预热期结束，开始正常推送")

                    # 跳过预热期的帧
                    continue

                # 🆕 帧完整性检查（轻量级，保证流畅度）
                # 预热后20帧内使用严格模式（平衡质量和流畅度）
                use_strict_mode = self._current_warmup_count > 0 and self._current_warmup_count < MJPEG_STRICT_MODE_WARMUP_LIMIT

                if not self._is_frame_valid(frame, strict=use_strict_mode):
                    self._invalid_frames_filtered += 1
                    logger.debug(f"⚠️ 帧{frame_count}完整性检查失败（严格模式={use_strict_mode}），已过滤")

                    # 如果有缓存的最后有效帧，使用它填充（避免播放器出现空白）
                    if self._last_valid_frame is not None:
                        frame = self._last_valid_frame
                        logger.debug(f"📦 使用上一个有效帧填充")
                    else:
                        # 如果没有缓存帧，跳过这一帧
                        continue
                else:
                    # ✨ 新增：高级帧质量评估（每5帧检查一次，平衡性能）
                    if frame_count % MJPEG_QUALITY_CHECK_INTERVAL == 0:
                        self._total_quality_checked += 1
                        quality_metrics = frame_quality_checker.check_frame_quality(
                            frame,
                            verbose=False,
                            enable_strict_mode=True  # 启用严格模式（局部质量+灰色帧检测）
                        )

                        # 🔧 质量阈值：质量分数>=70（较严格）
                        if quality_metrics.quality_score < 70.0:
                            self._low_quality_frames_filtered += 1
                            logger.debug(
                                f"⚠️ 帧{frame_count}质量不达标: "
                                f"质量分数={quality_metrics.quality_score:.2f}, "
                                f"清晰度={quality_metrics.sharpness:.2f}, "
                                f"对比度={quality_metrics.contrast:.2f}, 已过滤"
                            )

                            # 使用上一个高质量帧填充
                            if self._last_valid_frame is not None:
                                frame = self._last_valid_frame
                                logger.debug(f"📦 使用上一个高质量帧填充")
                            else:
                                continue
                        else:
                            # 缓存当前高质量帧
                            self._last_valid_frame = frame.copy()
                            logger.debug(
                                f"✅ 帧{frame_count}质量合格: "
                                f"质量分数={quality_metrics.quality_score:.2f}"
                            )
                    else:
                        # 非检查帧，直接缓存（假设连续帧质量相近）
                        self._last_valid_frame = frame.copy()

                # 压缩为JPEG（提高质量到90%，减少压缩导致的模糊）
                success, jpeg_buffer = cv2.imencode('.jpg', frame,
                    [cv2.IMWRITE_JPEG_QUALITY, MJPEG_JPEG_QUALITY])

                if success:
                    jpeg_bytes = jpeg_buffer.tobytes()
                    jpeg_size = len(jpeg_bytes)
                    if frame_count % MJPEG_LOG_INTERVAL == 0:
                        logger.info(f"✅ JPEG压缩成功，大小: {jpeg_size} bytes")

                    # 更新最新帧（非阻塞）
                    try:
                        if not self.frame_queue.full():
                            self.frame_queue.put(jpeg_bytes, block=False)
                            if frame_count % MJPEG_LOG_INTERVAL == 0:
                                logger.info(f"📦 帧已放入队列，队列大小: {self.frame_queue.qsize()}")
                        else:
                            # 丢弃旧帧，保持最新
                            try:
                                self.frame_queue.get_nowait()
                                if frame_count % MJPEG_LOG_INTERVAL == 0:
                                    logger.info(f"🗑️ 丢弃旧帧")
                            except Empty:
                                pass
                            self.frame_queue.put(jpeg_bytes, block=False)
                            if frame_count % MJPEG_LOG_INTERVAL == 0:
                                logger.info(f"📦 新帧已替换，队列大小: {self.frame_queue.qsize()}")
                    except Exception as queue_error:
                        logger.error(f"❌ 队列操作失败: {queue_error}")

                    self.last_frame_time = current_time
                else:
                    logger.error(f"❌ JPEG压缩失败: {self.stream_id}")

                # 每处理300帧输出一次状态并进行内存清理（减少日志频率）
                if frame_count % MJPEG_STATUS_LOG_INTERVAL == 0:
                    # 计算过滤率
                    invalid_filter_rate = (self._invalid_frames_filtered / self._total_frames_received * 100) if self._total_frames_received > 0 else 0
                    quality_filter_rate = (self._low_quality_frames_filtered / self._total_quality_checked * 100) if self._total_quality_checked > 0 else 0
                    logger.info(
                        f"📈 流处理状态 {self.stream_id}: "
                        f"已处理{frame_count}帧, "
                        f"队列大小={self.frame_queue.qsize()}, "
                        f"完整性过滤: {self._invalid_frames_filtered}/{self._total_frames_received} ({invalid_filter_rate:.2f}%), "
                        f"质量过滤: {self._low_quality_frames_filtered}/{self._total_quality_checked} ({quality_filter_rate:.2f}%)"
                    )
                    self._cleanup_memory()  # 定期内存清理

        except Exception as e:
            logger.error(f"❌ 流处理异常 {self.stream_id}: {e}")
            import traceback
            logger.error(f"📋 异常堆栈: {traceback.format_exc()}")
        finally:
            if cap:
                cap.release()
                logger.info(f"🔓 VideoCapture已释放: {self.stream_id}")
            self.running = False
            logger.info(f"🛑 流处理结束: {self.stream_id}")

    def _cleanup_memory(self):
        """内存清理和队列优化"""
        with self._lock:
            current_time = time.time()
            if current_time - self._last_cleanup_time > self._cleanup_interval:
                # 清空过时帧
                while not self.frame_queue.empty():
                    try:
                        self.frame_queue.get_nowait()
                    except Empty:
                        break
                self._last_cleanup_time = current_time
                logger.info(f"🧹 流 {self.stream_id} 内存清理完成")

    def get_latest_frame(self) -> Optional[bytes]:
        """获取最新帧"""
        try:
            frame = self.frame_queue.get_nowait()
            # 检查帧大小，防止内存泄漏
            if frame and len(frame) > self._frame_memory_limit:
                logger.warning(f"⚠️ 帧过大: {len(frame)} bytes，跳过")
                return None
            return frame
        except Empty:
            return None

    def stop(self):
        """停止处理"""
        logger.info(f"🛑 正在停止流处理: {self.stream_id}")
        self.running = False

        # 清空队列释放内存
        with self._lock:
            while not self.frame_queue.empty():
                try:
                    self.frame_queue.get_nowait()
                except Empty:
                    break

        logger.info(f"✅ 流处理已完全停止: {self.stream_id}")

# 全局管理器实例
stream_manager = MJPEGStreamManager()

@router.get("/stream/{rtsp_url:path}")
async def mjpeg_stream(rtsp_url: str):
    """
    企业级MJPEG流端点
    """
    # URL解码处理
    import urllib.parse
    decoded_rtsp_url = urllib.parse.unquote(rtsp_url)
    
    logger.info(f"🎯 [MJPEG] 接收到流请求")
    logger.info(f"🔗 原始URL: '{rtsp_url[:100]}{'...' if len(rtsp_url) > 100 else ''}'")
    logger.info(f"🔗 解码URL: '{decoded_rtsp_url[:100]}{'...' if len(decoded_rtsp_url) > 100 else ''}'")

    client_id = str(uuid.uuid4())
    stream_id = stream_manager.get_or_create_stream(decoded_rtsp_url)
    stream_manager.add_client(stream_id, client_id)

    def generate_mjpeg():
        """生成MJPEG流"""
        try:
            while True:
                frame_data = stream_manager.get_frame(stream_id)

                if frame_data:
                    # MJPEG多部分响应格式
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' +
                        frame_data + b'\r\n'
                    )
                else:
                    # NOTE(async): time.sleep 在此处合理 — generate_mjpeg 是同步生成器，
                    # StreamingResponse 在独立线程中执行同步迭代器
                    time.sleep(MJPEG_NO_FRAME_SLEEP)

        except Exception as e:
            logger.error(f"❌ MJPEG流生成异常: {e}")
        finally:
            stream_manager.remove_client(stream_id, client_id)

    return StreamingResponse(
        generate_mjpeg(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "X-Content-Type-Options": "nosniff",
        }
    )

@router.get("/health")
async def health_check():
    """健康检查"""
    active_streams = len(stream_manager.streams)
    total_clients = sum(len(clients) for clients in stream_manager.clients.values())

    return {
        "status": "healthy",
        "active_streams": active_streams,
        "total_clients": total_clients,
        "streams": {
            stream_id: len(stream_manager.clients.get(stream_id, []))
            for stream_id in stream_manager.streams.keys()
        }
    }