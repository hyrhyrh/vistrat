"""
RTSP视频流健康检查工具
提供RTSP流可用性验证和友好的错误提示
"""

import cv2
import logging
from typing import Dict, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class RTSPHealthChecker:
    """RTSP流健康检查器"""

    @staticmethod
    def check_rtsp_stream(rtsp_url: str, timeout: int = 10) -> Tuple[bool, str, Dict[str, Any]]:
        """
        检查RTSP流是否可用（多策略重试，借鉴MJPEG流服务的成功经验）

        参数:
            rtsp_url: RTSP流地址
            timeout: 基础超时时间(秒)，实际超时会根据策略调整

        返回:
            (is_healthy, error_message, stream_info)
            - is_healthy: 是否健康
            - error_message: 错误信息(如果不健康)
            - stream_info: 流信息(如果健康)
        """
        import os

        logger.info(f"开始检查RTSP流: {rtsp_url}")

        # 设置FFmpeg环境变量屏蔽详细日志
        os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
        os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # 静默模式

        # 设置OpenCV日志级别
        try:
            if hasattr(cv2, 'LOG_LEVEL_ERROR'):
                cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
            elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
                cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
            else:
                cv2.setLogLevel(2)  # ERROR级别
        except Exception:
            pass

        # 多策略尝试连接（借鉴MJPEG流服务的成功实现）
        strategies = [
            {
                "name": "FFmpeg+UDP+快速检测",
                "backend": cv2.CAP_FFMPEG,
                "env_options": 'rtsp_transport;udp|analyzeduration;1000000|probesize;3000000',
                "timeout_ms": max(15000, timeout * 1000),  # 至少15秒
            },
            {
                "name": "FFmpeg+TCP",
                "backend": cv2.CAP_FFMPEG,
                "env_options": 'rtsp_transport;tcp|analyzeduration;2000000|probesize;5000000',
                "timeout_ms": max(20000, timeout * 1000),  # 至少20秒
            },
            {
                "name": "默认后端",
                "backend": None,
                "env_options": None,
                "timeout_ms": max(10000, timeout * 1000),  # 至少10秒
            }
        ]

        last_error = None

        for strategy in strategies:
            cap = None
            try:
                logger.debug(f"尝试策略: {strategy['name']}")

                # 设置环境变量
                if strategy.get("env_options"):
                    os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = strategy["env_options"]
                elif 'OPENCV_FFMPEG_CAPTURE_OPTIONS' in os.environ:
                    del os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS']

                # 创建VideoCapture
                if strategy["backend"]:
                    cap = cv2.VideoCapture(rtsp_url, strategy["backend"])
                else:
                    cap = cv2.VideoCapture(rtsp_url)

                # 设置超时
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, strategy["timeout_ms"])
                cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, strategy["timeout_ms"] - 2000)

                # 检查是否成功打开
                if not cap.isOpened():
                    logger.debug(f"策略 {strategy['name']} 无法打开流")
                    last_error = "无法连接到RTSP流"
                    if cap:
                        cap.release()
                    continue

                # 尝试读取一帧验证
                ret, frame = cap.read()

                if not ret or frame is None:
                    logger.debug(f"策略 {strategy['name']} 无法读取帧")
                    last_error = "RTSP流已连接但无法读取视频帧"
                    cap.release()
                    continue

                # 成功！获取流信息
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = int(cap.get(cv2.CAP_PROP_FPS))

                stream_info = {
                    "width": width,
                    "height": height,
                    "fps": fps if fps > 0 else 25,
                    "resolution": f"{width}x{height}",
                    "checked_at": datetime.now().isoformat(),
                    "rtsp_url": rtsp_url,
                    "strategy": strategy['name']  # 记录成功的策略
                }

                cap.release()

                logger.info(f"RTSP流健康检查通过 [{strategy['name']}]: {rtsp_url}, 分辨率={width}x{height}, FPS={fps}")
                return True, "", stream_info

            except cv2.error as e:
                last_error = f"OpenCV错误: {str(e)}"
                logger.debug(f"策略 {strategy['name']} 失败: {e}")
                if cap:
                    cap.release()
                continue

            except Exception as e:
                last_error = f"未知错误: {str(e)}"
                logger.debug(f"策略 {strategy['name']} 异常: {e}")
                if cap:
                    cap.release()
                continue

        # 所有策略都失败了
        error_msg = f"{last_error or '所有连接策略失败'}\n可能原因:\n1. RTSP地址不正确\n2. 网络连接问题\n3. 摄像头离线\n4. 认证信息错误"
        logger.error(f"RTSP流健康检查失败（所有策略）: {rtsp_url}")
        return False, error_msg, {}

    @staticmethod
    def format_health_check_result(is_healthy: bool, error_message: str,
                                   stream_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化健康检查结果为API响应格式

        返回:
            {
                "healthy": bool,
                "message": str,
                "stream_info": dict,
                "suggestions": list
            }
        """
        if is_healthy:
            return {
                "healthy": True,
                "message": "RTSP流健康检查通过,可以启动分析",
                "stream_info": stream_info,
                "suggestions": []
            }
        else:
            suggestions = [
                "检查RTSP地址格式: rtsp://username:password@ip:port/path",
                "确认摄像头设备在线并可访问",
                "检查网络连接和防火墙设置",
                "验证RTSP端口(通常是554)是否开放",
                "确认摄像头支持的视频编码格式"
            ]

            return {
                "healthy": False,
                "message": error_message,
                "stream_info": {},
                "suggestions": suggestions
            }


# 创建全局实例
rtsp_health_checker = RTSPHealthChecker()
