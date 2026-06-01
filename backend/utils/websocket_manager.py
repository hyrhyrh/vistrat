"""
WebSocket连接管理器
提供统一的WebSocket连接管理和消息广播功能
"""

from typing import List, Dict, Any
from fastapi import WebSocket
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class WebSocketManager:
    """通用WebSocket连接管理器"""

    def __init__(self, name: str = "WebSocket"):
        self.name = name
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """接受新的WebSocket连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"{self.name} - 新连接建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """断开WebSocket连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"{self.name} - 连接断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """发送消息给特定客户端"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"{self.name} - 发送个人消息失败: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        """广播消息给所有连接的客户端"""
        if not self.active_connections:
            return

        logger.debug(f"{self.name} - 广播消息给 {len(self.active_connections)} 个客户端")

        # 移除失效的连接
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"{self.name} - 发送失败，移除连接: {e}")
                dead_connections.append(connection)

        for conn in dead_connections:
            self.disconnect(conn)

    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)

    def is_empty(self) -> bool:
        """检查是否没有活动连接"""
        return len(self.active_connections) == 0


class StreamHealthWSManager(WebSocketManager):
    """视频流健康状态WebSocket管理器"""

    def __init__(self):
        super().__init__(name="StreamHealth")

    async def broadcast_health_status(self, stream_id: str, health_data: Dict[str, Any]):
        """
        广播健康状态更新到所有连接的客户端

        Args:
            stream_id: 视频流ID
            health_data: 健康状态数据，包含:
                - health_status: online/offline/unknown
                - health_checked_at: 检查时间
                - health_error_message: 错误信息（可选）
                - health_stream_info: 流信息（可选）
        """
        from utils.timezone_utils import now_isoformat

        message = {
            "type": "health_update",
            "stream_id": stream_id,
            "data": health_data,
            "timestamp": now_isoformat()
        }

        await self.broadcast(message)

    async def broadcast_batch_health_status(self, updates: List[Dict[str, Any]]):
        """
        批量广播多个流的健康状态

        Args:
            updates: 更新列表，每项包含 stream_id 和 health_data
        """
        from utils.timezone_utils import now_isoformat

        message = {
            "type": "health_batch_update",
            "updates": updates,
            "timestamp": now_isoformat()
        }

        await self.broadcast(message)


# 全局单例实例
stream_health_ws_manager = StreamHealthWSManager()
