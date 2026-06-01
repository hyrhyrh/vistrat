"""
MJPEG帧处理辅助模块

从 api/mjpeg_stream.py 的 StreamProcessor 类中提取的帧处理相关功能：
- 帧完整性检查（基础和严格模式）
- OpenCV缓冲区清理
- 帧质量评估
- RTSP连接策略定义

这些方法原属于 StreamProcessor 类，提取为独立函数以降低主类复杂度。
"""

import logging
import os
import cv2
import numpy as np
from typing import Optional, List, Dict, Any

from core.constants import (
    FRAME_MEAN_BLACK_THRESHOLD, FRAME_MEAN_WHITE_THRESHOLD,
    FRAME_GRAY_MEAN_LOW, FRAME_GRAY_MEAN_HIGH, FRAME_GRAY_STD_THRESHOLD,
    FRAME_MIN_STD_THRESHOLD, FRAME_MIN_DIMENSION, FRAME_MAX_DIMENSION,
    FRAME_SIZE_MISMATCH_TOLERANCE,
    STRICT_LOW_VARIANCE_THRESHOLD, STRICT_LOW_VARIANCE_BLOCK_LIMIT, STRICT_MAX_BRIGHTNESS_DEVIATION,
    OPENCV_UDP_ANALYZE_DURATION, OPENCV_UDP_PROBE_SIZE,
    OPENCV_TCP_ANALYZE_DURATION, OPENCV_TCP_PROBE_SIZE,
    OPENCV_DEFAULT_ANALYZE_DURATION, OPENCV_DEFAULT_PROBE_SIZE,
    MJPEG_FPS_TARGET, MJPEG_OPENCV_BUFFER_CLEAR_COUNT,
)

logger = logging.getLogger(__name__)


def clear_opencv_buffer(cap: cv2.VideoCapture) -> None:
    """
    清空OpenCV缓冲区，避免读取旧的脏数据

    Args:
        cap: OpenCV VideoCapture对象
    """
    try:
        for _ in range(MJPEG_OPENCV_BUFFER_CLEAR_COUNT):
            cap.grab()
        logger.debug("已清空OpenCV缓冲区")
    except Exception as e:
        logger.warning(f"清空缓冲区失败: {e}")


def is_frame_valid(
    frame: np.ndarray,
    strict: bool = False,
    expected_frame_size: Optional[tuple] = None
) -> tuple:
    """
    帧完整性检查（增强版）

    Args:
        frame: 输入帧
        strict: 是否使用严格模式（重连后使用）
        expected_frame_size: 期望的帧尺寸 (width, height)，用于一致性检查

    Returns:
        (is_valid, new_expected_size, size_mismatch_count_delta)
        - is_valid: 帧是否有效
        - new_expected_size: 更新后的期望帧尺寸（None表示不更新）
        - size_mismatch_count_delta: 尺寸不匹配计数增量（0或1或-reset）
    """
    try:
        # 检查帧是否为空
        if frame is None or frame.size == 0:
            logger.debug("帧为空")
            return False, None, 0

        # 检查帧形状是否有效
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            logger.debug(f"帧形状无效: {frame.shape}")
            return False, None, 0

        # 检查帧尺寸是否合理
        height, width = frame.shape[:2]
        if width < FRAME_MIN_DIMENSION or height < FRAME_MIN_DIMENSION or width > FRAME_MAX_DIMENSION or height > FRAME_MAX_DIMENSION:
            logger.debug(f"帧尺寸异常: {width}x{height}")
            return False, None, 0

        # 检查是否为全黑帧
        mean_value = np.mean(frame)
        if mean_value < FRAME_MEAN_BLACK_THRESHOLD:
            logger.debug(f"检测到全黑帧，平均像素值={mean_value:.2f}")
            return False, None, 0

        # 检查是否为全白/过曝帧
        if mean_value > FRAME_MEAN_WHITE_THRESHOLD:
            logger.debug(f"检测到全白帧，平均像素值={mean_value:.2f}")
            return False, None, 0

        # 增强灰色帧检测
        if FRAME_GRAY_MEAN_LOW <= mean_value <= FRAME_GRAY_MEAN_HIGH:
            std_value = np.std(frame)
            if std_value < FRAME_GRAY_STD_THRESHOLD:
                logger.debug(f"检测到灰色帧: 亮度={mean_value:.2f}, 对比度={std_value:.2f}")
                return False, None, 0

        # 检查标准差（对比度），排除纯色帧
        std_value = np.std(frame)
        if std_value < FRAME_MIN_STD_THRESHOLD:
            logger.debug(f"检测到无对比度帧，标准差={std_value:.2f}")
            return False, None, 0

        # 严格模式：额外检查
        if strict:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape
            grid_h, grid_w = h // 4, w // 4
            block_variances = []
            block_means = []

            for i in range(4):
                for j in range(4):
                    y1, y2 = i * grid_h, (i + 1) * grid_h
                    x1, x2 = j * grid_w, (j + 1) * grid_w
                    block = gray[y1:y2, x1:x2]
                    block_variances.append(np.var(block))
                    block_means.append(np.mean(block))

            # 检查1：大部分块的方差都很低
            low_variance_count = sum(1 for v in block_variances if v < STRICT_LOW_VARIANCE_THRESHOLD)
            if low_variance_count > STRICT_LOW_VARIANCE_BLOCK_LIMIT:
                logger.debug(f"严格模式：检测到块状伪影，低方差块={low_variance_count}/16")
                return False, None, 0

            # 检查2：块之间的亮度差异过大
            mean_block_mean = np.mean(block_means)
            max_deviation = max(abs(m - mean_block_mean) for m in block_means)
            if max_deviation > STRICT_MAX_BRIGHTNESS_DEVIATION:
                logger.debug(f"严格模式：检测到局部亮度异常，最大偏离={max_deviation:.2f}")
                return False, None, 0

        return True, None, 0

    except Exception as e:
        logger.warning(f"帧完整性检查异常: {e}")
        return False, None, 0


def get_rtsp_connection_strategies() -> List[Dict[str, Any]]:
    """
    获取RTSP连接策略列表（按优先级排序）

    Returns:
        连接策略配置列表
    """
    return [
        {
            "name": "FFmpeg+UDP+分析优化",
            "backend": cv2.CAP_FFMPEG,
            "env_options": f'rtsp_transport;udp|analyzeduration;{OPENCV_UDP_ANALYZE_DURATION}|probesize;{OPENCV_UDP_PROBE_SIZE}',
            "options": {
                cv2.CAP_PROP_BUFFERSIZE: 3,
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 25000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC: 20000,
                cv2.CAP_PROP_FPS: MJPEG_FPS_TARGET,
            }
        },
        {
            "name": "FFmpeg+TCP",
            "backend": cv2.CAP_FFMPEG,
            "env_options": f'rtsp_transport;tcp|analyzeduration;{OPENCV_TCP_ANALYZE_DURATION}|probesize;{OPENCV_TCP_PROBE_SIZE}',
            "options": {
                cv2.CAP_PROP_BUFFERSIZE: 3,
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 30000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC: 25000,
            }
        },
        {
            "name": "默认后端+UDP",
            "backend": None,
            "env_options": f'rtsp_transport;udp|analyzeduration;{OPENCV_DEFAULT_ANALYZE_DURATION}|probesize;{OPENCV_DEFAULT_PROBE_SIZE}',
            "options": {
                cv2.CAP_PROP_BUFFERSIZE: 1,
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 20000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC: 15000,
            }
        },
        {
            "name": "简单模式",
            "backend": None,
            "env_options": None,
            "options": {
                cv2.CAP_PROP_BUFFERSIZE: 1,
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 15000,
            }
        }
    ]


def try_connect_rtsp(rtsp_url: str, strategies: List[Dict] = None) -> Optional[cv2.VideoCapture]:
    """
    使用多策略尝试连接RTSP流

    Args:
        rtsp_url: RTSP流地址
        strategies: 连接策略列表（默认使用标准策略）

    Returns:
        成功连接的VideoCapture对象，或None
    """
    if strategies is None:
        strategies = get_rtsp_connection_strategies()

    # 设置FFmpeg环境变量屏蔽详细日志
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
    os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'

    cap = None
    for strategy in strategies:
        logger.info(f"尝试策略: {strategy['name']}")

        try:
            # 设置环境变量
            if strategy.get("env_options"):
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = strategy["env_options"]
                logger.info(f"设置环境变量: {strategy['env_options']}")
            elif 'OPENCV_FFMPEG_CAPTURE_OPTIONS' in os.environ:
                del os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS']
                logger.info("清除环境变量")

            if strategy["backend"]:
                cap = cv2.VideoCapture(rtsp_url, strategy["backend"])
            else:
                cap = cv2.VideoCapture(rtsp_url)

            # 设置参数
            for prop, value in strategy["options"].items():
                cap.set(prop, value)

            # 测试连接
            if cap.isOpened():
                logger.info(f"{strategy['name']} 连接成功")

                # 立即测试读取
                test_ret, test_frame = cap.read()
                if test_ret and test_frame is not None:
                    logger.info(f"{strategy['name']} 首帧读取成功: {test_frame.shape}")
                    return cap
                else:
                    logger.warning(f"{strategy['name']} 无法读取帧")
                    cap.release()
                    cap = None
            else:
                logger.warning(f"{strategy['name']} 连接失败")
                cap.release()
                cap = None

        except Exception as e:
            logger.error(f"{strategy['name']} 异常: {e}")
            if cap:
                cap.release()
                cap = None

    logger.error("所有连接策略都失败了")
    return None
