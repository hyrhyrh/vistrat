"""
视频流WebSocket端点
提供实时健康状态推送
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import UUID
import logging
import asyncio
import json

from utils.websocket_manager import stream_health_ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video-streams", tags=["视频流WebSocket"])


@router.websocket("/ws/health-status")
async def websocket_health_status(websocket: WebSocket):
    """
    WebSocket端点：实时推送视频流健康状态更新

    连接后会自动接收健康检查结果推送

    消息格式:
    {
        "type": "health_update",
        "stream_id": "uuid",
        "data": {
            "health_status": "online/offline",
            "health_checked_at": "timestamp",
            "health_error_message": "error",
            "health_stream_info": {}
        },
        "timestamp": "timestamp"
    }

    客户端可以发送请求触发健康检查:
    {
        "action": "check_stream",
        "stream_id": "uuid"
    }

    或者触发批量检查:
    {
        "action": "check_all"
    }
    """
    await stream_health_ws_manager.connect(websocket)

    try:
        while True:
            # 保持连接，等待客户端消息
            data = await websocket.receive_text()

            # 处理客户端请求
            if data:
                try:
                    request = json.loads(data)
                    action = request.get("action")

                    if action == "check_stream":
                        # 触发单个流的健康检查
                        stream_id = request.get("stream_id")
                        if stream_id:
                            from api.video_streams import _trigger_background_health_check
                            asyncio.create_task(_trigger_background_health_check([UUID(stream_id)]))
                            await websocket.send_json({
                                "type": "ack",
                                "message": f"已触发流 {stream_id} 的健康检查"
                            })

                    elif action == "check_all":
                        # 触发所有流的健康检查
                        from services.video_stream_service import VideoStreamService
                        from api.video_streams import _trigger_background_health_check

                        streams = await VideoStreamService.get_streams(page=1, page_size=1000)
                        stream_ids = [s.id for s in streams]

                        asyncio.create_task(_trigger_background_health_check(stream_ids))
                        await websocket.send_json({
                            "type": "ack",
                            "message": f"已触发 {len(stream_ids)} 个流的健康检查"
                        })

                    elif action == "ping":
                        # 心跳检测
                        await websocket.send_json({
                            "type": "pong",
                            "timestamp": now_isoformat()
                        })

                except json.JSONDecodeError:
                    logger.warning(f"WebSocket收到无效JSON: {data}")
                except Exception as e:
                    logger.error(f"处理WebSocket请求失败: {e}")
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })

    except WebSocketDisconnect:
        stream_health_ws_manager.disconnect(websocket)
        logger.info("WebSocket客户端正常断开连接")
    except Exception as e:
        logger.error(f"WebSocket连接错误: {e}")
        stream_health_ws_manager.disconnect(websocket)


def now_isoformat():
    """获取当前时间ISO格式字符串"""
    from utils.timezone_utils import now_isoformat as get_now
    return get_now()
