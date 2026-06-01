#!/usr/bin/env python3
"""
测试StreamProcessor的OpenCV RTSP连接和帧获取
"""
import sys
import time
import logging
import cv2

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("test_stream_processor")

def test_opencv_connection(rtsp_url: str):
    """测试OpenCV连接和帧获取"""
    logger.info(f"🔍 开始测试RTSP流: {rtsp_url}")

    # 多策略尝试
    strategies = [
        {
            "name": "FFmpeg+UDP+分析优化",
            "backend": cv2.CAP_FFMPEG,
            "env_options": 'rtsp_transport;udp|analyzeduration;2000000|probesize;5000000',
            "options": {
                cv2.CAP_PROP_BUFFERSIZE: 3,
                cv2.CAP_PROP_OPEN_TIMEOUT_MSEC: 25000,
                cv2.CAP_PROP_READ_TIMEOUT_MSEC: 20000,
                cv2.CAP_PROP_FPS: 15,
            }
        },
    ]

    cap = None
    for strategy in strategies:
        logger.info(f"📝 尝试策略: {strategy['name']}")

        try:
            # 设置环境变量
            import os
            if strategy.get("env_options"):
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = strategy["env_options"]
                logger.info(f"🔧 设置环境变量: {strategy['env_options']}")

            if strategy["backend"]:
                cap = cv2.VideoCapture(rtsp_url, strategy["backend"])
            else:
                cap = cv2.VideoCapture(rtsp_url)

            # 设置参数
            for prop, value in strategy["options"].items():
                cap.set(prop, value)

            # 测试连接
            if cap.isOpened():
                logger.info(f"✅ {strategy['name']} VideoCapture已打开")

                # 获取流属性
                fps = cap.get(cv2.CAP_PROP_FPS)
                width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                logger.info(f"📊 流属性 - FPS: {fps}, 分辨率: {width}x{height}")

                # 立即测试读取
                logger.info("🎞️ 尝试读取首帧...")
                test_ret, test_frame = cap.read()
                if test_ret and test_frame is not None:
                    logger.info(f"✅ 首帧读取成功: {test_frame.shape}")

                    # 连续读取10帧
                    logger.info("🎞️ 尝试连续读取10帧...")
                    for i in range(10):
                        grabbed = cap.grab()
                        if not grabbed:
                            logger.warning(f"⚠️ grab()失败在第{i+1}帧")
                            break
                        ret, frame = cap.retrieve()
                        if not ret or frame is None:
                            logger.warning(f"⚠️ retrieve()失败在第{i+1}帧")
                            break
                        logger.info(f"✅ 第{i+1}帧读取成功: {frame.shape}")

                        # 测试JPEG编码
                        success, jpeg_buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 90])
                        if success:
                            jpeg_size = len(jpeg_buffer.tobytes())
                            logger.info(f"✅ JPEG编码成功，大小: {jpeg_size} bytes")
                        else:
                            logger.error("❌ JPEG编码失败")

                        time.sleep(0.1)

                    logger.info("✅ 测试成功完成")
                    return True
                else:
                    logger.warning(f"⚠️ {strategy['name']} 无法读取帧")
                    cap.release()
                    cap = None
            else:
                logger.warning(f"❌ {strategy['name']} VideoCapture未打开")
                cap.release()
                cap = None

        except Exception as e:
            logger.error(f"❌ {strategy['name']} 异常: {e}")
            import traceback
            logger.error(f"📋 异常堆栈: {traceback.format_exc()}")
            if cap:
                cap.release()
                cap = None

    logger.error("❌ 所有策略都失败")
    return False

if __name__ == "__main__":
    rtsp_url = "rtsp://192.168.1.100/ch1"
    if len(sys.argv) > 1:
        rtsp_url = sys.argv[1]

    test_opencv_connection(rtsp_url)
