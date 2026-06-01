"""
告警服务模块
负责实时告警推送和历史记录管理
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket

from models.alert import AlertMessage
from utils.timezone_utils import now, now_isoformat


logger = logging.getLogger(__name__)

# WebSocket认证配置：默认不强制认证（向后兼容）
WS_AUTH_REQUIRED = os.getenv("WS_AUTH_REQUIRED", "false").lower() == "true"


class AlertService:
    """告警服务"""

    _connections: Set[WebSocket] = set()
    _alert_history: list[AlertMessage] = []

    # 告警频次控制：记录最近发送的告警及时间
    # 格式：{alert_key: last_send_time}
    _alert_throttle_cache: Dict[str, datetime] = {}
    _throttle_interval_hours: int = 3  # 相同告警的最小间隔（小时）

    @classmethod
    async def register(cls, websocket: WebSocket, token: Optional[str] = None):
        """注册WebSocket连接，支持可选的token认证

        通过 query parameter 传递 token，例如: ws://host/alerts?token=xxx
        认证行为由环境变量 WS_AUTH_REQUIRED 控制：
        - false（默认）: 不强制认证，未提供token时记录debug日志
        - true: 强制认证，未提供或无效token时拒绝连接
        """
        if WS_AUTH_REQUIRED:
            if not token:
                logger.warning("WebSocket连接被拒绝: 未提供认证token（WS_AUTH_REQUIRED=true）")
                await websocket.close(code=4001, reason="认证token缺失")
                return False
            from services.auth_service import AuthService
            token_data = AuthService._verify_token(token)
            if token_data is None:
                logger.warning("WebSocket连接被拒绝: token无效或已过期")
                await websocket.close(code=4003, reason="认证token无效或已过期")
                return False
            logger.info(f"WebSocket认证成功: 用户 {token_data.username}")
        else:
            if not token:
                logger.debug("WebSocket连接未提供token（WS_AUTH_REQUIRED=false，允许匿名连接）")

        await websocket.accept()
        cls._connections.add(websocket)
        logger.info(f"WebSocket连接已注册，当前连接数: {len(cls._connections)}")
        return True

    @classmethod
    async def unregister(cls, websocket: WebSocket):
        """注销WebSocket连接"""
        cls._connections.discard(websocket)
        logger.info(f"WebSocket连接已注销，当前连接数: {len(cls._connections)}")

    @classmethod
    async def notify(cls, analysis_result: Dict[str, Any]):
        """广播告警信息"""
        try:
            # 创建告警消息
            alert_data = {
                "timestamp": now_isoformat(),
                "alert": analysis_result.get("alert", ""),
                "description": analysis_result.get("description", ""),
                "video_file_name": analysis_result.get("video_file_name"),
                "picture_file_name": analysis_result.get("picture_file_name"),
                "severity": cls._determine_severity(analysis_result.get("alert", ""))
            }
            
            alert = AlertMessage(**alert_data)
            
            # 添加到历史记录
            cls._alert_history.insert(0, alert)
            cls._alert_history = cls._alert_history[:1000]  # 保留最近1000条
            
            # 广播给所有连接的客户端
            message = json.dumps(alert_data, ensure_ascii=False)
            disconnected = set()
            
            for websocket in cls._connections:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    logger.warning(f"发送告警消息失败: {e}")
                    disconnected.add(websocket)
            
            # 清理断开的连接
            cls._connections -= disconnected
            
            logger.info(f"告警已广播给 {len(cls._connections)} 个客户端")
            
        except Exception as e:
            logger.error(f"告警通知失败: {str(e)}")

    @classmethod
    def _determine_severity(cls, alert_text: str) -> str:
        """根据告警内容判断严重程度"""
        if not alert_text or "无异常" in alert_text:
            return "low"
        
        high_severity_keywords = ["危险", "紧急", "火灾", "盗窃", "暴力"]
        medium_severity_keywords = ["异常", "注意", "可疑", "违规"]
        
        alert_lower = alert_text.lower()
        
        if any(keyword in alert_lower for keyword in high_severity_keywords):
            return "high"
        elif any(keyword in alert_lower for keyword in medium_severity_keywords):
            return "medium"
        else:
            return "low"

    @classmethod
    def get_history(cls, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """获取告警历史"""
        start_idx = offset
        end_idx = offset + limit
        
        alerts_slice = cls._alert_history[start_idx:end_idx]
        
        return {
            "data": [alert.dict() for alert in alerts_slice],
            "total": len(cls._alert_history),
            "page": offset // limit + 1,
            "page_size": limit
        }

    @classmethod
    async def broadcast_alert(cls, alert_message: Dict[str, Any]):
        """广播告警消息并存储到ES"""
        try:
            # 🔧 告警频次控制：生成告警唯一键
            # 使用消息类型+来源作为key（例如：HIGH_CPU_USAGE_性能监控系统）
            alert_key = f"{alert_message.get('message', 'unknown')}_{alert_message.get('source', 'unknown')}"

            # 检查是否在限制时间内已发送过相同告警
            current_time = now()
            if alert_key in cls._alert_throttle_cache:
                last_send_time = cls._alert_throttle_cache[alert_key]
                time_diff = current_time - last_send_time
                throttle_interval = timedelta(hours=cls._throttle_interval_hours)

                if time_diff < throttle_interval:
                    # 在限制时间内，跳过此次告警
                    remaining_time = throttle_interval - time_diff
                    remaining_minutes = int(remaining_time.total_seconds() / 60)
                    logger.info(
                        f"⏸️ 告警已限流: '{alert_message.get('message', '')}' "
                        f"距上次发送{int(time_diff.total_seconds() / 60)}分钟，"
                        f"需等待{remaining_minutes}分钟后才能再次发送"
                    )
                    return  # 跳过此次告警

            # 更新最后发送时间
            cls._alert_throttle_cache[alert_key] = current_time
            logger.info(f"✅ 告警通过频次检查: '{alert_message.get('message', '')}' (下次可发送时间: {cls._throttle_interval_hours}小时后)")

            # 转换为标准格式并调用现有的notify方法（用于WebSocket推送）
            analysis_result = {
                "alert": alert_message.get('message', ''),
                "description": alert_message.get('description', ''),
                "video_file_name": alert_message.get('source', ''),
                "picture_file_name": alert_message.get('image_path', '')
            }

            # 实时推送
            await cls.notify(analysis_result)
            
            # 存储到Elasticsearch
            from services.elasticsearch_service import elasticsearch_service
            
            # 调试日志：检查alert_message中的image_path
            image_path_from_alert = alert_message.get('image_path', '')
            logger.info(f"Alert_service存储 - 任务 {alert_message.get('task_id', 'unknown')}_帧{alert_message.get('frame_index', 0)}: image_path={image_path_from_alert}")
            
            # 准备ES存储格式
            # 使用北京时间生成时间戳（整个系统统一使用北京时间）
            from utils.timezone_utils import get_beijing_timestamp
            beijing_ts_ms = int(get_beijing_timestamp() * 1000)  # 北京时间毫秒时间戳

            es_alert_data = {
                "task_id": alert_message.get('task_id', ''),
                "video_id": alert_message.get('video_id', ''),
                "video_name": alert_message.get('title', '').replace('视频分析告警: ', ''),
                "frame_index": alert_message.get('frame_index', 0),
                "timestamp": alert_message.get('timestamp', 0.0),
                "video_time": cls._format_video_time(alert_message.get('timestamp', 0.0)),
                "template_name": alert_message.get('template_id', ''),  # 模板名称
                "analysis_type": 'video_analysis',  # 分析类型: 离线视频分析
                "confidence": alert_message.get('confidence', 0.0),
                "description": alert_message.get('message', ''),
                "severity": alert_message.get('severity', 'medium'),
                "created_at": beijing_ts_ms,  # 北京时间毫秒时间戳
                "algorithm_name": alert_message.get('template_id', ''),  # 算法名称（与template_name相同）
                "algorithm_category": alert_message.get('template_category', 'video_analysis'),
                "ai_response": alert_message.get('description', ''),
                "image_url": image_path_from_alert,
                "camera_name": None,  # 视频文件分析没有摄像头名称
                "detection_details": {
                    "confidence": alert_message.get('confidence', 0.0),
                    "frame_index": alert_message.get('frame_index', 0),
                    "source": alert_message.get('source', 'video_analysis'),
                    "template_category": alert_message.get('template_category', 'unknown')
                }
            }
            
            # 调试日志：检查es_alert_data中的image_url
            logger.info(f"Alert_service存储ES - 帧{alert_message.get('frame_index', 0)}: image_url={es_alert_data.get('image_url')}")
            
            # 存储到ES
            await elasticsearch_service.store_alert(es_alert_data)

            logger.info(f"告警已广播并存储到ES: {alert_message.get('id', 'unknown')}")
            
        except Exception as e:
            logger.error(f"广播告警失败: {e}")
    
    @classmethod
    def _format_video_time(cls, timestamp_seconds: float) -> str:
        """将秒数转换为MM:SS格式"""
        try:
            minutes = int(timestamp_seconds // 60)
            seconds = int(timestamp_seconds % 60)
            return f"{minutes:02d}:{seconds:02d}"
        except Exception:
            return "00:00"

    @classmethod
    def clear_history(cls):
        """清空告警历史"""
        cls._alert_history.clear()
        logger.info("告警历史已清空")