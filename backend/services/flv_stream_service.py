"""
HTTP-FLV视频流服务
用于替代MJPEG方案，提供无损H.264视频传输

架构：RTSP → FFmpeg转FLV → HTTP-FLV → flv.js播放器（广播模型）
优势：
1. 零重编码，完全无损
2. 延迟低（1-3秒）
3. 稳定性高（行业标准方案）
4. 支持多客户端并发播放（广播架构）
"""

import asyncio
import subprocess
import logging
import uuid
from typing import Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import signal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/flv", tags=["HTTP-FLV流媒体"])


def detect_nvidia_gpu() -> Tuple[bool, str]:
    """
    检测系统是否支持NVIDIA GPU硬件加速

    Returns:
        Tuple[bool, str]: (是否支持GPU, 检测信息)
    """
    try:
        # NOTE(async): subprocess.run 在此处合理 — detect_gpu_support 是同步初始化函数，仅在启动时调用一次
        result = subprocess.run(
            ['nvidia-smi', '-L'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0 and result.stdout:
            gpu_info = result.stdout.strip().split('\n')[0]  # 获取第一个GPU信息
            logger.info(f"✅ 检测到NVIDIA GPU: {gpu_info}")

            # 方法2: 验证FFmpeg是否支持h264_nvenc编码器
            ffmpeg_check = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if 'h264_nvenc' in ffmpeg_check.stdout:
                logger.info("✅ FFmpeg支持h264_nvenc硬件加速编码器")
                return True, f"GPU加速可用: {gpu_info}"
            else:
                logger.warning("⚠️ 检测到GPU但FFmpeg不支持h264_nvenc，将使用CPU转码")
                return False, "FFmpeg不支持h264_nvenc编码器"
        else:
            logger.info("ℹ️ 未检测到NVIDIA GPU，将使用CPU转码")
            return False, "未检测到NVIDIA GPU"

    except FileNotFoundError:
        logger.info("ℹ️ nvidia-smi命令不存在，将使用CPU转码")
        return False, "nvidia-smi命令不存在"
    except subprocess.TimeoutExpired:
        logger.warning("⚠️ GPU检测超时，将使用CPU转码")
        return False, "GPU检测超时"
    except Exception as e:
        logger.warning(f"⚠️ GPU检测失败: {e}，将使用CPU转码")
        return False, f"GPU检测异常: {str(e)}"


class FLVStreamBroadcaster:
    """
    单个FLV流的广播器

    架构：一个FFmpeg进程 → 一个读取器 → 广播给多个客户端
    解决问题：多个客户端不能同时从同一个stdout读取（会导致数据竞争）
    """

    def __init__(self, process: subprocess.Popen, stream_id: str):
        self.process = process
        self.stream_id = stream_id
        self.clients: Dict[str, asyncio.Queue] = {}
        self.reader_task: Optional[asyncio.Task] = None
        self.stderr_task: Optional[asyncio.Task] = None
        self.running = False

    async def monitor_stderr(self):
        """后台任务：监控FFmpeg stderr输出，提取编码信息"""
        loop = asyncio.get_event_loop()
        try:
            logger.info(f"🔍 开始监控FFmpeg stderr: {self.stream_id}")
            while self.running and self.process.poll() is None:
                line = await loop.run_in_executor(None, self.process.stderr.readline)
                if not line:
                    break

                line_str = line.decode('utf-8', errors='ignore').strip()

                # 提取关键信息：输入流编码信息
                if 'Stream #0:0' in line_str or 'Video:' in line_str:
                    logger.info(f"📹 [FFmpeg输入流信息] {line_str}")

                # 提取关键信息：输出编码信息
                if 'Output #0' in line_str or 'encoder' in line_str.lower():
                    logger.info(f"📤 [FFmpeg输出流信息] {line_str}")

                # 错误信息
                if 'error' in line_str.lower() or 'failed' in line_str.lower():
                    logger.warning(f"⚠️ [FFmpeg错误] {line_str}")

        except Exception as e:
            logger.error(f"❌ FFmpeg stderr监控异常: {e}")
        finally:
            logger.info(f"✅ FFmpeg stderr监控结束: {self.stream_id}")

    async def start_reading(self):
        """后台任务：读取FFmpeg输出并广播给所有客户端"""
        self.running = True
        loop = asyncio.get_event_loop()
        chunk_count = 0
        total_bytes = 0

        try:
            logger.info(f"📡 开始FLV流广播: {self.stream_id}")

            while self.running and self.process.poll() is None:
                # 从FFmpeg读取数据
                chunk = await loop.run_in_executor(None, self.process.stdout.read, 4096)

                if not chunk:
                    logger.warning(f"⚠️ FFmpeg输出结束: {self.stream_id}")
                    # 通知所有客户端流结束
                    for queue in list(self.clients.values()):
                        try:
                            await queue.put(None)
                        except Exception:
                            pass  # 通知客户端流结束，忽略队列异常
                    break

                chunk_count += 1
                total_bytes += len(chunk)

                # 广播给所有客户端（不缓存FLV头，避免时间戳不连续问题）
                dead_clients = []
                for client_id, queue in list(self.clients.items()):
                    try:
                        # 非阻塞put，如果队列满了就跳过（客户端消费太慢）
                        queue.put_nowait(chunk)
                    except asyncio.QueueFull:
                        logger.warning(f"⚠️ 客户端队列已满，跳过此chunk: {client_id}")
                    except Exception as e:
                        logger.warning(f"⚠️ 客户端队列异常，标记移除: {client_id}, error={e}")
                        dead_clients.append(client_id)

                # 清理死亡客户端
                for client_id in dead_clients:
                    self.remove_client(client_id)

                # 每1000个chunk输出一次日志
                if chunk_count % 1000 == 0:
                    logger.info(f"📊 FLV流广播: {self.stream_id}, chunks={chunk_count}, "
                              f"total_bytes={total_bytes / 1024 / 1024:.2f}MB, clients={len(self.clients)}")

        except Exception as e:
            logger.error(f"❌ FLV流广播异常: {e}")
            import traceback
            logger.error(f"📋 异常堆栈: {traceback.format_exc()}")
        finally:
            self.running = False
            logger.info(f"✅ FLV流广播结束: {self.stream_id}, total_bytes={total_bytes / 1024 / 1024:.2f}MB")

            # 通知所有剩余客户端
            for queue in list(self.clients.values()):
                try:
                    await queue.put(None)
                except Exception:
                    pass  # 清理阶段通知客户端，忽略队列异常

    def add_client(self, client_id: str) -> asyncio.Queue:
        """添加客户端订阅，返回数据队列"""
        queue = asyncio.Queue(maxsize=200)  # 限制队列大小避免内存溢出（约800KB缓冲）
        self.clients[client_id] = queue
        logger.info(f"📺 客户端订阅FLV流: stream={self.stream_id}, client={client_id[:8]}..., "
                  f"当前客户端数: {len(self.clients)}")
        return queue

    def remove_client(self, client_id: str):
        """移除客户端订阅"""
        if client_id in self.clients:
            try:
                # 清空队列
                queue = self.clients[client_id]
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except Exception:
                        break  # 队列已空或状态异常，停止清理
            except Exception:
                pass  # 队列清理失败不影响客户端移除
            finally:
                del self.clients[client_id]
                logger.info(f"📺 客户端取消订阅: stream={self.stream_id}, client={client_id[:8]}..., 剩余客户端数: {len(self.clients)}")

    def has_clients(self) -> bool:
        """是否还有客户端"""
        return len(self.clients) > 0

    def get_client_count(self) -> int:
        """获取客户端数量"""
        return len(self.clients)


class FLVStreamManager:
    """HTTP-FLV流管理器（支持多客户端广播）"""

    def __init__(self):
        self.broadcasters: Dict[str, FLVStreamBroadcaster] = {}

        # GPU支持检测（启动时检测一次，缓存结果）
        self.gpu_available, self.gpu_info = detect_nvidia_gpu()
        if self.gpu_available:
            logger.info(f"🚀 FLV流服务启用GPU加速: {self.gpu_info}")
        else:
            logger.info(f"💻 FLV流服务使用CPU转码: {self.gpu_info}")

    def start_flv_stream(self, rtsp_url: str, stream_id: str) -> subprocess.Popen:
        """
        启动FFmpeg RTSP → FLV转换进程

        Args:
            rtsp_url: RTSP流地址
            stream_id: 流唯一标识

        Returns:
            FFmpeg进程对象
        """
        # FFmpeg基础命令参数
        ffmpeg_cmd = [
            'ffmpeg',
            # 输入参数
            '-rtsp_transport', 'tcp',      # 使用TCP传输（更稳定）
            '-rtsp_flags', 'prefer_tcp',   # 优先TCP
            '-analyzeduration', '2000000',  # 分析时长2秒
            '-probesize', '5000000',        # 探测大小5MB
            '-allowed_media_types', 'video', # 只处理视频
            '-i', rtsp_url,                 # 输入RTSP流
        ]

        # 动态选择编码参数（GPU优先，CPU备选）
        if self.gpu_available:
            # GPU硬件加速编码（NVIDIA h264_nvenc）
            video_params = [
                '-c:v', 'h264_nvenc',       # NVIDIA GPU硬件编码器（速度提升10倍）
                '-preset', 'p4',            # NVENC预设：p4质量更好（p1最快，p7最慢）
                '-tune', 'hq',              # 高质量模式（High Quality）
                '-rc', 'vbr',               # 可变比特率模式
                '-cq', '23',                # 恒定质量：23为高质量（与CPU CRF一致）
                '-b:v', '4M',               # 目标比特率4Mbps（1080p推荐）
                '-maxrate', '6M',           # 最大比特率6Mbps
                '-bufsize', '4M',           # 缓冲区大小
                '-g', '15',                 # 🔧 GOP大小15帧（更多I帧，减少模糊）
                '-bf', '0',                 # 禁用B帧（降低延迟）
                '-forced-idr', '1',         # 强制IDR帧（确保关键帧）
                '-profile:v', 'high',       # H.264 high profile
                '-level', '4.0',            # H.264 level 4.0
                '-s', '1920x1080',          # 输出分辨率1080p
                '-r', '15',                 # 输出帧率15fps
            ]
            logger.info(f"🚀 使用GPU加速编码: h264_nvenc (1080p高质量, GOP=15, 更多I帧)")
        else:
            # CPU软件编码（libx264）- 优化模式（提升画质，减少模糊）
            video_params = [
                '-c:v', 'libx264',          # CPU软件编码器
                '-preset', 'faster',        # 快速编码预设（比veryfast更快）
                '-tune', 'zerolatency',     # 零延迟优化
                '-crf', '23',               # 🔧 质量23（提升画质：24 → 23）
                '-g', '15',                 # 🔧 GOP大小15帧（更多I帧，减少模糊）
                '-keyint_min', '15',        # 🔧 最小关键帧间隔15帧
                '-bf', '0',                 # 🔧 禁用B帧（只使用I帧和P帧）
                '-sc_threshold', '0',       # 🔧 禁用场景切换检测（强制固定GOP）
                '-profile:v', 'main',       # H.264 main profile（平衡兼容性和画质）
                '-level', '4.0',            # H.264 level 4.0
                '-pix_fmt', 'yuv420p',      # 像素格式
                '-s', '1280x720',           # 输出分辨率720p（确保速度）
                '-r', '15',                 # 输出帧率15fps
                '-threads', '4',            # 使用4线程
            ]
            logger.info(f"💻 使用CPU软件编码: libx264 (720p高质量模式, GOP=15, 更多I帧)")

        # 组装完整命令
        ffmpeg_cmd.extend(video_params)
        ffmpeg_cmd.extend([
            # 音频参数
            '-an',                          # 禁用音频

            # FLV输出参数
            '-f', 'flv',                    # 输出FLV格式
            '-flvflags', 'no_duration_filesize',  # 去除duration和filesize

            # 错误恢复
            '-err_detect', 'ignore_err',    # 忽略错误
            '-fflags', '+genpts',           # 生成PTS时间戳

            # 输出到stdout
            'pipe:1'
        ])

        logger.info(f"🎬 启动FFmpeg进程: {stream_id}")
        logger.info(f"📝 FFmpeg命令: {' '.join(ffmpeg_cmd[:8])}...")  # 只打印前8个参数避免日志过长

        try:
            # NOTE(async): subprocess.Popen 在此处合理 — FFmpeg 长期运行子进程，需要通过管道持续读取流数据
            # 注意：preexec_fn 只在 Unix 系统上可用，Windows 需要使用不同的方式
            import sys
            if sys.platform == 'win32':
                # Windows平台：不使用 preexec_fn
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1024 * 1024,  # 1MB缓冲区
                    creationflags=subprocess.CREATE_NO_WINDOW  # Windows: 不创建控制台窗口
                )
            else:
                # Unix平台：使用 preexec_fn 处理 SIGPIPE
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    bufsize=1024 * 1024,  # 1MB缓冲区
                    preexec_fn=lambda: signal.signal(signal.SIGPIPE, signal.SIG_DFL)
                )

            logger.info(f"✅ FFmpeg进程已启动: PID={process.pid}, stream_id={stream_id}")

            return process

        except Exception as e:
            logger.error(f"❌ FFmpeg进程启动失败: {e}")
            raise

    def stop_broadcaster(self, stream_id: str):
        """停止广播器和FFmpeg进程"""
        if stream_id in self.broadcasters:
            broadcaster = self.broadcasters[stream_id]
            try:
                # 停止广播任务
                broadcaster.running = False
                if broadcaster.reader_task:
                    broadcaster.reader_task.cancel()
                if broadcaster.stderr_task:
                    broadcaster.stderr_task.cancel()

                # 停止FFmpeg进程
                process = broadcaster.process
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    logger.warning(f"⚠️ FFmpeg进程被强制终止: {stream_id}")

                logger.info(f"🛑 FLV广播器已停止: {stream_id}")
            except Exception as e:
                logger.error(f"❌ 停止FLV广播器失败: {e}")
            finally:
                del self.broadcasters[stream_id]

    def create_dedicated_broadcaster(self, rtsp_url: str) -> tuple[str, FLVStreamBroadcaster]:
        """
        为每个客户端创建独立的广播器（多进程模式）

        原因：广播模式下新客户端会错过FLV头，导致flv.js无法解析
        策略：每个客户端独立的FFmpeg进程，确保获得完整的FLV流
        """
        import uuid
        # 使用UUID确保每个客户端有独立的stream_id
        stream_id = f"flv_{hash(rtsp_url)}_{uuid.uuid4().hex[:8]}"

        # 创建新的FFmpeg进程
        process = self.start_flv_stream(rtsp_url, stream_id)

        # 创建广播器
        broadcaster = FLVStreamBroadcaster(process, stream_id)
        self.broadcasters[stream_id] = broadcaster

        # 启动读取任务和stderr监控任务
        broadcaster.reader_task = asyncio.create_task(broadcaster.start_reading())
        broadcaster.stderr_task = asyncio.create_task(broadcaster.monitor_stderr())

        logger.info(f"✅ 创建专用FLV广播器: {stream_id}")
        return stream_id, broadcaster

    def check_and_cleanup_idle_broadcasters(self):
        """检查并清理没有客户端的广播器"""
        idle_streams = []
        for stream_id, broadcaster in self.broadcasters.items():
            if not broadcaster.has_clients():
                idle_streams.append(stream_id)

        for stream_id in idle_streams:
            logger.info(f"🧹 清理空闲广播器: {stream_id}")
            self.stop_broadcaster(stream_id)


# 全局流管理器实例
flv_manager = FLVStreamManager()


@router.get("/stream/{rtsp_url:path}")
async def get_flv_stream(rtsp_url: str):
    """
    HTTP-FLV流端点（多进程模式）

    Args:
        rtsp_url: RTSP流地址（URL编码）

    Returns:
        StreamingResponse: FLV视频流
    """
    import urllib.parse
    decoded_rtsp_url = urllib.parse.unquote(rtsp_url)

    logger.info(f"🎯 [HTTP-FLV] 接收到流请求")
    logger.info(f"🔗 原始URL: '{rtsp_url[:50]}{'...' if len(rtsp_url) > 50 else ''}'")
    logger.info(f"🔗 解码URL: '{decoded_rtsp_url[:50]}{'...' if len(decoded_rtsp_url) > 50 else ''}'")

    try:
        # 为每个客户端创建独立的广播器
        stream_id, broadcaster = flv_manager.create_dedicated_broadcaster(decoded_rtsp_url)

        # 为客户端创建独立的数据队列
        client_id = str(uuid.uuid4())
        client_queue = broadcaster.add_client(client_id)

        async def generate_flv():
            """从客户端队列读取数据（每个客户端独立）"""
            try:
                logger.info(f"📤 开始从队列推送FLV数据: client_id={client_id[:8]}...")

                chunk_count = 0
                total_bytes = 0

                while True:
                    # 从客户端专属队列读取数据（非阻塞）
                    try:
                        chunk = await asyncio.wait_for(client_queue.get(), timeout=10.0)
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ 客户端队列读取超时: {client_id[:8]}...")
                        break

                    # None表示流结束
                    if chunk is None:
                        logger.info(f"📭 收到流结束信号: {client_id[:8]}...")
                        break

                    chunk_count += 1
                    total_bytes += len(chunk)

                    # 每1000个chunk输出一次日志
                    if chunk_count % 1000 == 0:
                        logger.info(f"📊 客户端FLV流状态: client={client_id[:8]}..., chunks={chunk_count}, "
                                  f"total_bytes={total_bytes / 1024 / 1024:.2f}MB, queue_size={client_queue.qsize()}")

                    yield chunk

            except asyncio.CancelledError:
                logger.info(f"🔌 客户端取消连接: {client_id[:8]}...")
            except BrokenPipeError:
                logger.info(f"🔌 客户端断开连接: {client_id[:8]}...")
            except Exception as e:
                logger.error(f"❌ FLV流异常: client={client_id[:8]}..., error={e}")
                import traceback
                logger.error(f"📋 异常堆栈: {traceback.format_exc()}")
            finally:
                logger.info(f"✅ 客户端FLV流结束: client={client_id[:8]}..., total_bytes={total_bytes / 1024 / 1024:.2f}MB")
                # 移除客户端订阅
                broadcaster.remove_client(client_id)
                # 检查是否需要清理空闲广播器
                if not broadcaster.has_clients():
                    logger.info(f"🧹 广播器无客户端，将在下次清理时停止: {stream_id}")
                    # 异步清理（延迟5秒，避免短时间内重新连接）
                    asyncio.create_task(delayed_cleanup(stream_id))

        async def delayed_cleanup(stream_id: str):
            """延迟清理空闲广播器"""
            await asyncio.sleep(5)
            if stream_id in flv_manager.broadcasters:
                broadcaster = flv_manager.broadcasters[stream_id]
                if not broadcaster.has_clients():
                    logger.info(f"🧹 执行延迟清理: {stream_id}")
                    flv_manager.stop_broadcaster(stream_id)

        # 返回流响应
        return StreamingResponse(
            generate_flv(),
            media_type="video/x-flv",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "X-Content-Type-Options": "nosniff",
            }
        )

    except Exception as e:
        logger.error(f"❌ HTTP-FLV流处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查（多进程模式）"""
    active_broadcasters = len(flv_manager.broadcasters)
    total_clients = sum(b.get_client_count() for b in flv_manager.broadcasters.values())

    # 检查广播器状态
    broadcaster_status = {}
    for stream_id, broadcaster in flv_manager.broadcasters.items():
        is_alive = broadcaster.process.poll() is None
        is_running = broadcaster.running
        broadcaster_status[stream_id] = {
            "process_alive": is_alive,
            "broadcaster_running": is_running,
            "pid": broadcaster.process.pid if is_alive else None,
            "clients": broadcaster.get_client_count(),
            "reader_task_done": broadcaster.reader_task.done() if broadcaster.reader_task else None
        }

    return {
        "status": "healthy",
        "architecture": "multi-process",  # 每个客户端独立FFmpeg进程
        "active_broadcasters": active_broadcasters,
        "total_clients": total_clients,
        "broadcasters": broadcaster_status
    }
