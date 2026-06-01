"""
视频流快照API
提供从RTSP流获取静态快照的接口
"""

import cv2
import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from io import BytesIO
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/snapshot", tags=["视频快照"])


@router.get("/stream/{rtsp_url:path}", summary="获取RTSP流快照")
async def get_stream_snapshot(rtsp_url: str):
    """
    从RTSP流获取单帧快照
    
    Args:
        rtsp_url: RTSP流地址
        
    Returns:
        JPEG格式的图片
    """
    try:
        # 参数验证
        if not rtsp_url or rtsp_url.strip() == "" or rtsp_url == "undefined":
            raise HTTPException(status_code=400, detail="RTSP URL不能为空或undefined")
        
        logger.info(f"[快照] 开始获取RTSP流快照: {rtsp_url}")
        
        # 在线程池中运行OpenCV操作，避免阻塞
        def capture_frame():
            cap = None
            try:
                logger.info(f"[快照] 尝试连接RTSP流: {rtsp_url}")
                # 创建VideoCapture对象
                cap = cv2.VideoCapture(rtsp_url)
                
                # 设置更宽松的参数
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                # 注意：CAP_PROP_TIMEOUT在某些OpenCV版本中不可用，跳过设置
                try:
                    cap.set(cv2.CAP_PROP_TIMEOUT, 10000)  # 10秒超时
                except AttributeError:
                    logger.info("[快照] OpenCV版本不支持CAP_PROP_TIMEOUT，跳过超时设置")
                
                # 尝试设置合理的分辨率
                try:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                except Exception:
                    logger.info("[快照] 分辨率设置失败，使用默认值")
                
                if not cap.isOpened():
                    logger.error(f"[快照] 无法打开RTSP流: {rtsp_url}")
                    return None
                
                logger.info("[快照] RTSP流连接成功，开始读取帧")
                
                # 跳过几帧获取最新内容，但如果第一帧成功就直接使用
                success_frame = None
                for i in range(5):  # 尝试读取5帧
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        success_frame = frame
                        logger.info(f"[快照] 成功读取第{i+1}帧，尺寸: {frame.shape}")
                        if i == 0:  # 如果第一帧就成功，直接使用
                            break
                    else:
                        logger.warning(f"[快照] 读取第{i+1}帧失败")
                
                if success_frame is None:
                    logger.error("[快照] 所有帧读取都失败")
                    return None
                
                logger.info(f"[快照] 最终获取帧成功，尺寸: {success_frame.shape}")
                return success_frame
                
            except Exception as e:
                logger.error(f"[快照] OpenCV处理失败: {e}")
                return None
            finally:
                if cap:
                    cap.release()
                    logger.info("[快照] VideoCapture已释放")
        
        # NOTE(async): OpenCV VideoCapture 是阻塞调用，必须在线程池中运行
        loop = asyncio.get_event_loop()
        frame = await loop.run_in_executor(None, capture_frame)
        
        if frame is None:
            raise HTTPException(status_code=500, detail="无法获取视频帧")
        
        # 转换为JPEG格式
        try:
            # 转换BGR到RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 使用PIL转换为JPEG
            pil_image = Image.fromarray(frame_rgb)
            
            # 保存为JPEG格式到内存
            img_buffer = BytesIO()
            pil_image.save(img_buffer, format='JPEG', quality=85, optimize=True)
            img_buffer.seek(0)
            
            logger.info("[快照] 图片转换成功")
            
            # 返回图片响应
            return Response(
                content=img_buffer.getvalue(),
                media_type="image/jpeg",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
            
        except Exception as convert_error:
            logger.error(f"[快照] 图片格式转换失败: {convert_error}")
            raise HTTPException(status_code=500, detail="图片格式转换失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[快照] 获取快照失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取快照失败: {str(e)}")


@router.get("/test", summary="快照功能测试")
async def test_snapshot():
    """测试快照功能是否正常"""
    try:
        # 创建一个测试图片
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        test_image[:] = (100, 150, 200)  # 填充颜色
        
        # 添加测试文字
        cv2.putText(test_image, 'Snapshot Test', (50, 240), 
                   cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
        
        # 转换为PIL图片
        pil_image = Image.fromarray(cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB))
        
        # 保存为JPEG
        img_buffer = BytesIO()
        pil_image.save(img_buffer, format='JPEG', quality=85)
        img_buffer.seek(0)
        
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/jpeg"
        )
        
    except Exception as e:
        logger.error(f"[快照] 测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")