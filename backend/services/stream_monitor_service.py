"""
基于FFmpeg + OpenCV的专业流媒体监控服务
- 自动检测流状态（正常/异常/离线）
- FFmpeg推流到HLS/WebRTC
- OpenCV实时分析流质量
- 自动状态管理和恢复
"""

import asyncio
import logging
import os
import time
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

import cv2
import numpy as np
import ffmpeg
from sqlalchemy.orm import Session

from models.video_stream import VideoStreamDB, StreamStatusEnum
from database.connection import DatabaseManager
from utils.timezone_utils import now, now_isoformat
from config.settings import PathConfig

logger = logging.getLogger(__name__)


class StreamHealthChecker:
    """流健康状态检查器"""
    
    def __init__(self):
        self.frame_buffer = {}  # 存储最近的帧用于分析
        self.last_check = {}   # 最后检查时间
        
    def analyze_frame_quality(self, frame: np.ndarray) -> Dict[str, Any]:
        """分析帧质量"""
        if frame is None or frame.size == 0:
            return {"healthy": False, "reason": "empty_frame"}
            
        try:
            # 1. 检查帧尺寸
            height, width = frame.shape[:2]
            if height < 100 or width < 100:
                return {"healthy": False, "reason": "frame_too_small", "resolution": f"{width}x{height}"}
            
            # 2. 检查是否全黑或全白
            mean_brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
            if mean_brightness < 5:
                return {"healthy": False, "reason": "black_screen", "brightness": mean_brightness}
            elif mean_brightness > 250:
                return {"healthy": False, "reason": "white_screen", "brightness": mean_brightness}
            
            # 3. 检查图像方差（判断是否静止画面）
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            if variance < 100:
                return {"healthy": False, "reason": "static_image", "variance": variance}
            
            # 4. 检查颜色分布
            channels = cv2.split(frame)
            color_variance = [np.var(channel) for channel in channels]
            if all(var < 10 for var in color_variance):
                return {"healthy": False, "reason": "low_color_variance", "color_variance": color_variance}
            
            return {
                "healthy": True,
                "resolution": f"{width}x{height}",
                "brightness": mean_brightness,
                "variance": variance,
                "color_variance": color_variance
            }
            
        except Exception as e:
            logger.error(f"分析帧质量时出错: {e}")
            return {"healthy": False, "reason": "analysis_error", "error": str(e)}
    
    def _quick_frame_analysis(self, frame: np.ndarray) -> Dict[str, Any]:
        """快速帧质量分析 - 简化版本，减少计算开销"""
        if frame is None or frame.size == 0:
            return {"healthy": False, "reason": "empty_frame"}
            
        try:
            # 只做基本检查
            height, width = frame.shape[:2]
            if height < 50 or width < 50:
                return {"healthy": False, "reason": "frame_too_small"}
            
            # 简化亮度检查
            mean_brightness = np.mean(frame)
            if mean_brightness < 10 or mean_brightness > 245:
                return {"healthy": False, "reason": "brightness_issue"}
            
            return {"healthy": True, "brightness": mean_brightness}
            
        except Exception as e:
            return {"healthy": False, "reason": "quick_analysis_error", "error": str(e)}
    
    def check_stream_health(self, stream_url: str, max_check_frames: int = 3) -> Dict[str, Any]:
        """检查流健康状态 - 优化版本，避免长时间阻塞"""
        try:
            # 设置OpenCV超时参数（5秒）
            cap = cv2.VideoCapture(stream_url)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)  # 5秒连接超时
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 3000)  # 3秒读取超时
            
            # 检查是否能够打开流（快速检查）
            start_time = time.time()
            if not cap.isOpened():
                cap.release()
                return {
                    "healthy": False, 
                    "reason": "cannot_open_stream", 
                    "url": stream_url,
                    "timestamp": now_isoformat(),
                    "check_duration": time.time() - start_time
                }
            
            # 检查连接时间是否超时
            if time.time() - start_time > 8:  # 8秒总超时
                cap.release()
                return {
                    "healthy": False,
                    "reason": "connection_timeout", 
                    "url": stream_url,
                    "timestamp": now_isoformat(),
                    "check_duration": time.time() - start_time
                }
            
            # 快速获取流基本信息
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # 减少帧检查数量，快速分析
            healthy_frames = 0
            total_frames = 0
            frame_analyses = []
            
            for i in range(max_check_frames):
                # 检查总时间是否超限
                if time.time() - start_time > 10:  # 10秒绝对超时
                    logger.warning(f"流检查超时，已处理{total_frames}帧: {stream_url}")
                    break
                    
                frame_start = time.time()
                ret, frame = cap.read()
                
                # 单帧读取超时检查
                if time.time() - frame_start > 2:  # 单帧2秒超时
                    logger.warning(f"单帧读取超时: {stream_url}")
                    break
                    
                if not ret:
                    break
                    
                total_frames += 1
                # 简化的帧质量分析
                analysis = self._quick_frame_analysis(frame)
                frame_analyses.append(analysis)
                
                if analysis["healthy"]:
                    healthy_frames += 1
            
            cap.release()
            
            # 判断整体健康状态
            health_ratio = healthy_frames / max(total_frames, 1)
            is_healthy = health_ratio >= 0.5 and total_frames > 0  # 降低阈值，至少有帧才算健康
            
            total_duration = time.time() - start_time
            
            return {
                "healthy": is_healthy,
                "health_ratio": health_ratio,
                "healthy_frames": healthy_frames,
                "total_frames": total_frames,
                "stream_info": {
                    "fps": fps if fps > 0 else "unknown",
                    "resolution": f"{width}x{height}" if width > 0 and height > 0 else "unknown",
                    "width": width,
                    "height": height
                },
                "frame_analyses": frame_analyses,
                "url": stream_url,
                "timestamp": now_isoformat(),
                "check_duration": round(total_duration, 2)
            }
            
        except Exception as e:
            total_duration = time.time() - start_time if 'start_time' in locals() else 0
            logger.error(f"检查流健康状态时出错 ({total_duration:.2f}s): {e}")
            return {
                "healthy": False,
                "reason": "check_error",
                "error": str(e),
                "url": stream_url,
                "timestamp": now_isoformat(),
                "check_duration": round(total_duration, 2)
            }


class FFmpegStreamManager:
    """FFmpeg流管理器"""

    def __init__(self):
        self.active_processes = {}  # 活跃的FFmpeg进程
        # 使用PathConfig统一管理路径，跨平台兼容（Windows/Linux/Docker）
        self.hls_output_dir = PathConfig.HLS_STREAMS_DIR
        self.hls_output_dir.mkdir(parents=True, exist_ok=True)
    
    def _find_ffmpeg_executable(self) -> Optional[str]:
        """查找可用的FFmpeg可执行文件"""
        # 可能的FFmpeg路径列表
        possible_paths = [
            'ffmpeg',                    # 系统PATH中
            '/usr/bin/ffmpeg',          # 标准系统位置
            '/usr/local/bin/ffmpeg',    # 本地安装
            '/opt/ffmpeg/bin/ffmpeg',   # 可选安装位置
            '/snap/bin/ffmpeg',         # Snap包
            './ffmpeg',                 # 当前目录
        ]
        
        for path in possible_paths:
            try:
                # NOTE(async): subprocess.run 在此处合理 — _find_ffmpeg_executable 是同步初始化方法
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    logger.info(f"Found FFmpeg at: {path}")
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        logger.error("FFmpeg executable not found in any standard location")
        return None
    
    def create_hls_stream(self, stream_id: str, rtsp_url: str, output_quality: str = "720p") -> Dict[str, Any]:
        """创建HLS流"""
        try:
            # 定义输出路径
            output_dir = self.hls_output_dir / stream_id
            output_dir.mkdir(exist_ok=True)
            
            playlist_path = output_dir / "playlist.m3u8"
            
            # 根据质量设置参数
            quality_settings = {
                "1080p": {"scale": "1920:1080", "bitrate": "5000k"},
                "720p": {"scale": "1280:720", "bitrate": "3000k"},
                "480p": {"scale": "854:480", "bitrate": "1500k"},
                "360p": {"scale": "640:360", "bitrate": "800k"}
            }
            
            settings = quality_settings.get(output_quality, quality_settings["720p"])
            
            # 构建FFmpeg命令 - 支持多种FFmpeg路径
            ffmpeg_executable = self._find_ffmpeg_executable()
            if not ffmpeg_executable:
                error_msg = (
                    "FFmpeg not found. For production deployment, please:\n"
                    "1. Docker: FROM jrottenberg/ffmpeg:4.4-alpine\n"
                    "2. Ubuntu/Debian: apt install -y ffmpeg\n"
                    "3. CentOS/RHEL: yum install -y ffmpeg\n"
                    "4. Manual: Download from https://ffmpeg.org/download.html"
                )
                raise Exception(error_msg)
            
            ffmpeg_cmd = [
                ffmpeg_executable,
                '-y',  # 覆盖输出文件
                '-i', rtsp_url,
                '-c:v', 'libx264',
                '-preset', 'veryfast',
                '-tune', 'zerolatency',
                '-c:a', 'aac',
                '-b:a', '128k',
                '-b:v', settings['bitrate'],
                '-maxrate', settings['bitrate'],
                '-bufsize', str(int(settings['bitrate'].replace('k', '')) * 2) + 'k',
                '-vf', f"scale={settings['scale']}",
                '-g', '50',
                '-sc_threshold', '0',
                '-hls_time', '2',
                '-hls_list_size', '10',
                '-hls_flags', 'delete_segments',
                '-f', 'hls',
                str(playlist_path)
            ]
            
            # NOTE(async): subprocess.Popen 在此处合理 — FFmpeg 长期运行子进程，需要持续读取管道输出
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            self.active_processes[stream_id] = {
                "process": process,
                "cmd": ffmpeg_cmd,
                "output_path": str(playlist_path),
                "output_dir": str(output_dir),
                "started_at": now(),
                "quality": output_quality
            }
            
            logger.info(f"FFmpeg HLS流已启动: {stream_id} -> {playlist_path}")
            
            return {
                "success": True,
                "stream_id": stream_id,
                "hls_url": f"/hls/{stream_id}/playlist.m3u8",
                "output_path": str(playlist_path),
                "quality": output_quality
            }
            
        except Exception as e:
            logger.error(f"创建HLS流时出错: {e}")
            return {
                "success": False,
                "error": str(e),
                "stream_id": stream_id
            }
    
    def stop_stream(self, stream_id: str) -> bool:
        """停止流处理"""
        if stream_id not in self.active_processes:
            return False
            
        try:
            process_info = self.active_processes[stream_id]
            process = process_info["process"]
            
            # 优雅地终止进程
            process.terminate()
            
            # 等待进程结束
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            
            # 清理输出文件
            output_dir = Path(process_info["output_dir"])
            if output_dir.exists():
                for file in output_dir.glob("*"):
                    file.unlink()
                output_dir.rmdir()
            
            del self.active_processes[stream_id]
            logger.info(f"FFmpeg流已停止: {stream_id}")
            return True
            
        except Exception as e:
            logger.error(f"停止流时出错: {e}")
            return False
    
    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """获取流状态"""
        if stream_id not in self.active_processes:
            return {"active": False, "stream_id": stream_id}
        
        process_info = self.active_processes[stream_id]
        process = process_info["process"]
        
        return {
            "active": process.poll() is None,
            "stream_id": stream_id,
            "pid": process.pid,
            "started_at": process_info["started_at"].isoformat(),
            "output_path": process_info["output_path"],
            "quality": process_info["quality"],
            "uptime_seconds": (now() - process_info["started_at"]).total_seconds()
        }


class StreamMonitorService:
    """流监控服务主类"""
    
    def __init__(self):
        self.health_checker = StreamHealthChecker()
        self.ffmpeg_manager = FFmpegStreamManager()
        self.monitor_interval = 30  # 监控间隔（秒）
        self.running = False
        self.monitor_thread = None
        # 延迟初始化线程池（兼容ARM/Windows）
        self.executor = None
        self._executor_initialized = False

    def _ensure_executor(self):
        """延迟创建线程池（兼容ARM/Windows）"""
        if self._executor_initialized:
            return

        try:
            # 尝试创建线程池
            self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="stream_check")
            self._executor_initialized = True
            logger.info("✅ StreamMonitor线程池创建成功（max_workers=3）")
        except Exception as e:
            self.executor = None
            self._executor_initialized = True
            logger.warning(f"⚠️ StreamMonitor线程池创建失败（ARM/Windows限制），某些功能可能不可用: {e}")

    def start_monitoring(self):
        """启动监控服务（已禁用threading.Thread以兼容ARM）"""
        logger.warning("⚠️ StreamMonitorService.start_monitoring() 当前未启用（ARM/Windows兼容性）")
        logger.warning("⚠️ 如需使用此功能，请改用asyncio实现替代threading.Thread")
        return

        # 原代码（已注释以避免ARM线程创建问题）:
        # if self.running:
        #     logger.warning("监控服务已在运行中")
        #     return
        #
        # self.running = True
        # self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        # self.monitor_thread.start()
        # logger.info("流监控服务已启动")
    
    def stop_monitoring(self):
        """停止监控服务"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=10)
        
        # 关闭线程池
        if self.executor:
            self.executor.shutdown(wait=True)
        
        # 停止所有FFmpeg进程
        for stream_id in list(self.ffmpeg_manager.active_processes.keys()):
            self.ffmpeg_manager.stop_stream(stream_id)
        
        logger.info("流监控服务已停止")
    
    def _monitor_loop(self):
        """监控循环（当前已禁用，保留供未来参考）"""
        # NOTE(async): time.sleep 在此处合理 — _monitor_loop 设计为在独立线程中运行
        while self.running:
            try:
                self._check_all_streams()
                time.sleep(self.monitor_interval)
            except Exception as e:
                logger.error(f"监控循环中出错: {e}")
                time.sleep(5)  # 出错后短暂休息
    
    def _check_all_streams(self):
        """检查所有流状态 - 使用异步处理避免阻塞"""
        try:
            with DatabaseManager.get_sync_session() as session:
                streams = session.query(VideoStreamDB).all()
                
                # 使用线程池并发检查流状态，设置超时
                futures = []
                for stream in streams:
                    future = self.executor.submit(self._check_single_stream_safe, stream)
                    futures.append((stream, future))
                
                # 收集结果，设置每个任务15秒超时
                for stream, future in futures:
                    try:
                        health_result = future.result(timeout=15)
                        
                        if health_result is None:
                            continue
                            
                        # 根据健康状态更新数据库
                        new_status = StreamStatusEnum.ONLINE if health_result["healthy"] else StreamStatusEnum.OFFLINE
                        
                        if stream.status != new_status:
                            stream.status = new_status
                            session.commit()
                            
                            logger.info(f"流状态已更新: {stream.name} ({stream.id}) -> {new_status.value} (耗时: {health_result.get('check_duration', 'unknown')}s)")
                            
                            # 如果流变为在线，启动HLS推流
                            if new_status == StreamStatusEnum.ONLINE:
                                self.start_hls_stream(str(stream.id), stream.stream_url)
                            # 如果流变为离线，停止HLS推流
                            elif new_status == StreamStatusEnum.OFFLINE:
                                self.stop_hls_stream(str(stream.id))
                    
                    except FutureTimeoutError:
                        logger.warning(f"检查流超时(15s): {stream.name}")
                        continue
                    except Exception as e:
                        logger.error(f"检查流 {stream.name} 时出错: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"检查所有流时出错: {e}")
    
    def _check_single_stream_safe(self, stream) -> Optional[Dict[str, Any]]:
        """安全的单流检查 - 在独立线程中运行"""
        try:
            return self.health_checker.check_stream_health(stream.stream_url)
        except Exception as e:
            logger.error(f"单流检查异常 {stream.name}: {e}")
            return None
    
    def start_hls_stream(self, stream_id: str, rtsp_url: str, quality: str = "720p") -> Dict[str, Any]:
        """启动HLS流"""
        return self.ffmpeg_manager.create_hls_stream(stream_id, rtsp_url, quality)
    
    def stop_hls_stream(self, stream_id: str) -> bool:
        """停止HLS流"""
        return self.ffmpeg_manager.stop_stream(stream_id)
    
    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """获取流状态"""
        return self.ffmpeg_manager.get_stream_status(stream_id)
    
    def check_stream_health_now(self, stream_url: str, timeout: int = 12) -> Dict[str, Any]:
        """立即检查流健康状态 - 非阻塞版本"""
        try:
            # 使用线程池执行，避免阻塞API响应
            future = self.executor.submit(self.health_checker.check_stream_health, stream_url)
            result = future.result(timeout=timeout)
            return result
        except FutureTimeoutError:
            logger.warning(f"立即检查流健康状态超时({timeout}s): {stream_url}")
            return {
                "healthy": False,
                "reason": "health_check_timeout",
                "url": stream_url,
                "timestamp": now_isoformat(),
                "check_duration": timeout
            }
        except Exception as e:
            logger.error(f"立即检查流健康状态异常: {e}")
            return {
                "healthy": False,
                "reason": "health_check_error",
                "error": str(e),
                "url": stream_url,
                "timestamp": now_isoformat()
            }
    
    def get_monitor_status(self) -> Dict[str, Any]:
        """获取监控服务状态"""
        return {
            "running": self.running,
            "monitor_interval": self.monitor_interval,
            "active_streams": len(self.ffmpeg_manager.active_processes),
            "active_stream_ids": list(self.ffmpeg_manager.active_processes.keys())
        }


# 全局监控服务实例
stream_monitor = StreamMonitorService()