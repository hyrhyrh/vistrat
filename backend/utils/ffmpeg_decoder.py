"""
FFmpeg专业视频解码器
提供比OpenCV更高质量的RTSP流解码
企业级解决方案：杜绝乱码、模糊、灰色帧
"""

import subprocess
import numpy as np
import cv2
import logging
import queue
import threading
from typing import Optional, Tuple
from dataclasses import dataclass
import time

from core.constants import (
    FFMPEG_ANALYZE_DURATION, FFMPEG_PROBE_SIZE, FFMPEG_MAX_DELAY,
    FFMPEG_DECODE_THREADS, FFMPEG_DEFAULT_FPS, FFMPEG_DEFAULT_WIDTH,
    FFMPEG_DEFAULT_HEIGHT, FFMPEG_PROCESS_BUFFER_SIZE,
    FFMPEG_FRAME_QUEUE_SIZE, FFMPEG_RECONNECT_INTERVAL,
    FFMPEG_DECODER_ALIVE_TIMEOUT, FFMPEG_CONSECUTIVE_READ_FAILURES_LIMIT,
    FFMPEG_STREAM_ANALYZE_DURATION, FFMPEG_STREAM_PROBE_SIZE,
)

logger = logging.getLogger(__name__)


@dataclass
class FFmpegConfig:
    """FFmpeg解码配置"""
    # RTSP传输协议
    rtsp_transport: str = "tcp"  # tcp更稳定，udp更快但可能丢包

    # 解码器选项
    hwaccel: Optional[str] = None  # 硬件加速：'cuda', 'qsv', 'videotoolbox', None
    decoder: str = "h264"  # 解码器：h264, hevc等

    # 缓冲设置
    analyzeduration: int = FFMPEG_ANALYZE_DURATION  # 分析时长(微秒)
    probesize: int = FFMPEG_PROBE_SIZE  # 探测大小(字节)
    max_delay: int = FFMPEG_MAX_DELAY  # 最大延迟(微秒)

    # 帧提取设置
    fps_filter: Optional[float] = None  # 降帧率：None表示不降帧
    skip_frame: str = "nokey"  # 跳帧策略：'nokey'=只要关键帧, 'none'=全部帧

    # 质量设置
    flags: str = "low_delay"  # 低延迟模式
    threads: int = FFMPEG_DECODE_THREADS  # 解码线程数

    # 输出设置
    pix_fmt: str = "bgr24"  # OpenCV兼容的BGR24格式

    def to_ffmpeg_args(self, rtsp_url: str, width: int = 0, height: int = 0) -> list:
        """
        生成FFmpeg命令行参数（深度优化版：处理PPS错误和分辨率问题）

        Args:
            rtsp_url: RTSP流地址
            width: 目标宽度（0=保持原始）
            height: 目标高度（0=保持原始）

        Returns:
            FFmpeg命令参数列表
        """
        args = [
            'ffmpeg',
            '-y',  # 覆盖输出
            '-loglevel', 'warning',  # 显示警告和错误信息

            # 🔧 深度优化：容错性参数
            '-fflags', '+genpts+igndts+discardcorrupt',  # 生成PTS、忽略DTS、丢弃损坏帧
            '-flags', 'low_delay',  # 低延迟模式

            # 🔧 RTSP优化参数
            '-rtsp_transport', self.rtsp_transport,  # TCP传输
            '-rtsp_flags', 'prefer_tcp',  # 偏好TCP
            '-allowed_media_types', 'video',  # 只接收视频

            # 🔧 缓冲和探测优化
            '-analyzeduration', str(self.analyzeduration),  # 分析时长
            '-probesize', str(self.probesize),  # 探测大小
            '-max_delay', str(self.max_delay),  # 最大延迟
        ]

        # 硬件加速
        if self.hwaccel:
            args.extend(['-hwaccel', self.hwaccel])

        # 输入URL
        args.extend(['-i', rtsp_url])

        # 🔧 视频解码优化
        args.extend([
            '-vsync', 'passthrough',  # 保持原始时间戳
            '-threads', str(self.threads),  # 解码线程数
        ])

        # ✨ 关键修复：只解码I帧（跳过P帧和B帧）
        if self.skip_frame and self.skip_frame != "none":
            args.extend(['-skip_frame', self.skip_frame])
            logger.info(f"✅ FFmpeg跳帧策略: {self.skip_frame} (只解码{'I帧' if self.skip_frame == 'nokey' else '部分帧'})")

        # 帧率控制
        if self.fps_filter:
            args.extend(['-r', str(self.fps_filter)])

        # 视频过滤器
        vf_filters = []
        if width > 0 and height > 0:
            vf_filters.append(f'scale={width}:{height}')
        if vf_filters:
            args.extend(['-vf', ','.join(vf_filters)])

        # 输出格式
        args.extend([
            '-f', 'rawvideo',  # 原始视频流
            '-pix_fmt', self.pix_fmt,
            'pipe:1'  # 输出到stdout
        ])

        return args


class FFmpegDecoder:
    """
    FFmpeg专业解码器

    特点：
    1. 只解码I帧（关键帧），跳过P/B帧，确保质量
    2. TCP传输，避免UDP丢包
    3. 大缓冲区，减少网络抖动
    4. 企业级质量保证
    """

    def __init__(
        self,
        rtsp_url: str,
        config: Optional[FFmpegConfig] = None,
        frame_queue_size: int = FFMPEG_FRAME_QUEUE_SIZE,
        reconnect_interval: int = FFMPEG_RECONNECT_INTERVAL
    ):
        """
        初始化FFmpeg解码器

        Args:
            rtsp_url: RTSP流地址
            config: FFmpeg配置
            frame_queue_size: 帧队列大小
            reconnect_interval: 重连间隔(秒)
        """
        self.rtsp_url = rtsp_url
        self.config = config or FFmpegConfig()
        self.frame_queue_size = frame_queue_size
        self.reconnect_interval = reconnect_interval

        # NOTE(async): FFmpeg 子进程和解码线程必须使用 threading + subprocess —
        # FFmpeg 通过 stdin/stdout 管道进行二进制帧数据传输，无法使用纯异步方式替代
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.decode_thread: Optional[threading.Thread] = None
        self.stderr_thread: Optional[threading.Thread] = None  # stderr读取线程

        # 帧队列
        self.frame_queue: queue.Queue = queue.Queue(maxsize=frame_queue_size)

        # 流信息
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.fps: float = FFMPEG_DEFAULT_FPS

        # 统计信息
        self.total_frames_decoded = 0
        self.total_frames_dropped = 0
        self.last_frame_time = 0

        # 🔧 进程跟踪：防止僵尸进程
        self.process_pid: Optional[int] = None  # 记录当前进程PID，用于调试和清理

    def _probe_stream(self) -> Tuple[int, int, float]:
        """
        探测流信息（分辨率、帧率）- 深度优化版

        Returns:
            (width, height, fps)
        """
        # 🔧 方法1: 使用ffprobe（最准确）
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',  # 静默模式
                '-print_format', 'json',  # JSON格式输出
                '-show_streams',  # 显示流信息
                '-select_streams', 'v:0',  # 只选择第一个视频流
                '-rtsp_transport', self.config.rtsp_transport,
                '-analyzeduration', str(FFMPEG_STREAM_ANALYZE_DURATION),
                '-probesize', str(FFMPEG_STREAM_PROBE_SIZE),
                self.rtsp_url
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                import json
                probe_data = json.loads(result.stdout)

                if 'streams' in probe_data and len(probe_data['streams']) > 0:
                    stream = probe_data['streams'][0]
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)

                    # 解析帧率
                    fps = FFMPEG_DEFAULT_FPS
                    if 'r_frame_rate' in stream:
                        fps_str = stream['r_frame_rate']
                        if '/' in fps_str:
                            num, den = fps_str.split('/')
                            if int(den) > 0:
                                fps = float(num) / float(den)

                    if width > 0 and height > 0:
                        logger.info(f"✅ [ffprobe] 探测流信息: {width}x{height} @ {fps}fps")
                        return width, height, fps
        except Exception as e:
            logger.warning(f"⚠️ [ffprobe] 探测失败: {e}")

        # 🔧 方法2: 使用ffmpeg解码第一帧获取真实分辨率（备用方案）
        try:
            logger.info("🔄 尝试备用方案：解码第一帧获取分辨率...")
            cmd = [
                'ffmpeg',
                '-rtsp_transport', self.config.rtsp_transport,
                '-i', self.rtsp_url,
                '-frames:v', '1',  # 只解码1帧
                '-f', 'null',
                '-'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            stderr = result.stderr

            # 从stderr中解析分辨率和帧率
            import re
            # 查找 "Stream #0:0: Video: h264, yuv420p, 2560x1440"
            resolution_match = re.search(r'(\d{3,4})x(\d{3,4})', stderr)
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr)

            if resolution_match:
                width = int(resolution_match.group(1))
                height = int(resolution_match.group(2))
                fps = float(fps_match.group(1)) if fps_match else FFMPEG_DEFAULT_FPS

                logger.info(f"✅ [ffmpeg备用] 探测流信息: {width}x{height} @ {fps}fps")
                return width, height, fps

        except Exception as e:
            logger.warning(f"⚠️ [ffmpeg备用] 探测失败: {e}")

        # 返回默认值（作为最后的fallback）
        logger.warning(f"⚠️ 所有探测方法失败，使用默认分辨率 {FFMPEG_DEFAULT_WIDTH}x{FFMPEG_DEFAULT_HEIGHT}")
        return FFMPEG_DEFAULT_WIDTH, FFMPEG_DEFAULT_HEIGHT, FFMPEG_DEFAULT_FPS

    def _stderr_reader(self):
        """
        异步读取FFmpeg的stderr输出（避免管道堵塞）

        这是关键！如果不持续读取stderr，缓冲区满了FFmpeg就会阻塞
        """
        if not self.process or not self.process.stderr:
            return

        try:
            for line in iter(self.process.stderr.readline, b''):
                if not self.is_running:
                    break
                # 只记录WARNING和ERROR级别的信息
                line_text = line.decode('utf-8', errors='ignore').strip()
                if line_text and ('error' in line_text.lower() or 'warning' in line_text.lower()):
                    logger.debug(f"[FFmpeg stderr] {line_text}")
        except Exception as e:
            logger.debug(f"stderr读取线程退出: {e}")

    def _cleanup_old_process(self):
        """
        清理旧的FFmpeg进程（强制终止）
        确保不会产生僵尸进程
        """
        if self.process:
            old_pid = self.process.pid if self.process.pid else self.process_pid
            logger.info(f"🧹 开始清理旧FFmpeg进程 (PID: {old_pid})")

            try:
                # 尝试优雅终止
                if self.process.poll() is None:  # 进程还在运行
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=2)
                        logger.info(f"✅ 进程 {old_pid} 已优雅终止")
                    except subprocess.TimeoutExpired:
                        # 超时后强制杀死
                        logger.warning(f"⚠️ 进程 {old_pid} 未响应terminate，强制kill")
                        self.process.kill()
                        self.process.wait(timeout=1)
                        logger.info(f"✅ 进程 {old_pid} 已强制终止")
                else:
                    # 进程已退出，但需要回收僵尸进程
                    self.process.wait()
                    logger.info(f"✅ 进程 {old_pid} 已回收")

            except Exception as e:
                logger.error(f"❌ 清理进程 {old_pid} 时出错: {e}")
                # 最后的手段：使用系统命令强制杀死
                if old_pid:
                    try:
                        import os
                        import signal
                        os.kill(old_pid, signal.SIGKILL)
                        logger.info(f"✅ 使用SIGKILL终止进程 {old_pid}")
                    except Exception:
                        pass  # SIGKILL清理失败，进程可能已退出
            finally:
                self.process = None
                self.process_pid = None

    def _start_ffmpeg_process(self) -> bool:
        """
        启动FFmpeg解码进程

        Returns:
            是否成功启动
        """
        try:
            # 🔧 关键修复：启动前先清理任何现有进程
            if self.process is not None:
                logger.warning(f"⚠️ 检测到已存在的FFmpeg进程，先清理")
                self._cleanup_old_process()

            # 探测流信息
            self.width, self.height, self.fps = self._probe_stream()

            # ✨ 生成FFmpeg命令（不传入width/height，避免不必要的scale操作）
            cmd = self.config.to_ffmpeg_args(self.rtsp_url, 0, 0)

            logger.info(f"🚀 启动FFmpeg解码器: {' '.join(cmd[:15])}...")

            # 启动进程
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=FFMPEG_PROCESS_BUFFER_SIZE
            )

            # 🔧 记录进程PID
            self.process_pid = self.process.pid

            # 🔧 启动stderr读取线程（避免管道堵塞！）
            self.stderr_thread = threading.Thread(target=self._stderr_reader, daemon=True)
            self.stderr_thread.start()

            logger.info(f"✅ FFmpeg进程已启动 (PID: {self.process_pid})")
            return True

        except Exception as e:
            logger.error(f"❌ 启动FFmpeg进程失败: {e}")
            return False

    def _decode_loop(self):
        """解码循环（在独立线程中运行）- 优化版"""
        frame_size = self.width * self.height * 3  # BGR24 = 3 bytes per pixel
        reconnect_count = 0
        consecutive_read_failures = 0  # 连续读取失败计数

        # 🔧 给FFmpeg一点时间建立RTSP连接
        logger.info(f"⏳ 等待FFmpeg建立RTSP连接...")
        time.sleep(2)

        while self.is_running:
            try:
                # 🔧 只在真正需要时检查进程状态（不要在每次循环开始时检查）
                # 因为FFmpeg可能需要时间建立连接，过早检查会误判

                # 读取一帧
                try:
                    raw_frame = self.process.stdout.read(frame_size)
                except Exception as read_error:
                    logger.error(f"❌ 读取stdout失败: {read_error}")
                    raw_frame = b''

                if len(raw_frame) != frame_size:
                    consecutive_read_failures += 1
                    logger.warning(f"⚠️ 读取帧不完整: {len(raw_frame)}/{frame_size} bytes (连续失败: {consecutive_read_failures})")

                    # 检查进程是否已退出
                    if self.process.poll() is not None:
                        # 🔧 进程已退出，不要使用communicate()因为stderr已被独立线程读取
                        logger.error(f"❌ FFmpeg进程异常退出 (PID: {self.process_pid}, 返回码: {self.process.returncode})，stderr详情见上方日志")

                        # 🔧 使用统一的清理方法
                        self._cleanup_old_process()

                        # 尝试重连
                        reconnect_count += 1
                        logger.warning(f"🔄 尝试重连 FFmpeg ({reconnect_count})...")

                        if not self._start_ffmpeg_process():
                            logger.error(f"❌ 重连失败，{self.reconnect_interval}秒后重试")
                            time.sleep(self.reconnect_interval)
                            continue

                        reconnect_count = 0
                        consecutive_read_failures = 0
                        # 🔧 重连成功，更新last_frame_time避免被误判为"已死亡"
                        self.last_frame_time = time.time()
                        # 重新建立连接后等待
                        time.sleep(2)
                    elif consecutive_read_failures >= FFMPEG_CONSECUTIVE_READ_FAILURES_LIMIT:
                        # 连续失败太多次，可能FFmpeg卡住了，强制重启
                        logger.error(f"❌ 连续{consecutive_read_failures}次读取失败，强制重启FFmpeg...")

                        # 🔧 使用统一的清理方法
                        self._cleanup_old_process()

                        consecutive_read_failures = 0
                        time.sleep(1)

                    continue

                # 成功读取，重置失败计数
                consecutive_read_failures = 0

                # 转换为numpy数组
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))

                # 添加到队列
                try:
                    self.frame_queue.put(frame, block=False)
                    self.total_frames_decoded += 1
                    self.last_frame_time = time.time()
                except queue.Full:
                    # 队列满，丢弃旧帧
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put(frame, block=False)
                        self.total_frames_dropped += 1
                    except Exception:
                        pass  # 队列操作竞争条件，丢弃当前帧

            except Exception as e:
                logger.error(f"❌ 解码循环错误: {e}")
                time.sleep(0.1)

    def start(self) -> bool:
        """
        启动解码器

        Returns:
            是否成功启动
        """
        if self.is_running:
            logger.warning("⚠️ 解码器已在运行")
            return True

        # 启动FFmpeg进程
        if not self._start_ffmpeg_process():
            return False

        # 启动解码线程
        self.is_running = True
        # 🔧 关键修复：初始化last_frame_time为当前时间，避免启动时被误判为"已死亡"
        self.last_frame_time = time.time()
        self.decode_thread = threading.Thread(target=self._decode_loop, daemon=True)
        self.decode_thread.start()

        logger.info("✅ FFmpeg解码器已启动")
        return True

    def read(self, timeout: float = 1.0) -> Tuple[bool, Optional[np.ndarray]]:
        """
        读取一帧

        Args:
            timeout: 超时时间(秒)

        Returns:
            (是否成功, 帧数据)
        """
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return True, frame
        except queue.Empty:
            return False, None

    def stop(self):
        """停止解码器"""
        logger.info(f"🛑 开始停止FFmpeg解码器 (PID: {self.process_pid})")
        self.is_running = False

        # 🔧 使用统一的清理方法停止FFmpeg进程
        self._cleanup_old_process()

        # 等待解码线程结束
        if self.decode_thread:
            self.decode_thread.join(timeout=2)
            self.decode_thread = None

        # 🔧 等待stderr线程结束
        if self.stderr_thread:
            self.stderr_thread.join(timeout=1)
            self.stderr_thread = None

        logger.info(
            f"✅ FFmpeg解码器已停止 "
            f"(解码{self.total_frames_decoded}帧, 丢弃{self.total_frames_dropped}帧)"
        )

    def __del__(self):
        """
        析构函数：确保对象销毁时清理进程
        防止进程泄漏
        """
        try:
            if self.process is not None or self.process_pid is not None:
                logger.warning(f"⚠️ FFmpegDecoder对象被销毁但进程未清理 (PID: {self.process_pid})，执行清理")
                self.stop()
        except Exception:
            # 析构函数中不应抛出异常
            pass

    def is_alive(self) -> bool:
        """检查解码器是否存活

        超时时间设置为120秒（2分钟），以容忍：
        - RTSP流的网络波动和暂时中断
        - 时间配置导致的帧跳过期间
        - FFmpeg进程的短暂卡顿
        """
        if not self.is_running:
            return False
        if not self.process or self.process.poll() is not None:
            return False
        # 检查最近是否有帧
        return (time.time() - self.last_frame_time) < FFMPEG_DECODER_ALIVE_TIMEOUT

    def restart(self) -> bool:
        """安全重启 ffmpeg 进程"""
        self.stop()
        try:
            return self.start()
        except Exception:
            return False

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'is_running': self.is_running,
            'is_alive': self.is_alive(),
            'total_frames_decoded': self.total_frames_decoded,
            'total_frames_dropped': self.total_frames_dropped,
            'queue_size': self.frame_queue.qsize(),
            'fps': self.fps,
            'resolution': f'{self.width}x{self.height}' if self.width else 'unknown'
        }

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
