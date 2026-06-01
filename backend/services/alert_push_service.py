"""统一推送服务 -- 企业微信 + Telegram，fire-and-log 模式"""

import logging
import time
from typing import Optional

from config.settings import AlertConfig, ServerConfig
from services.notification_adapters import (
    NotificationMessage,
    NotificationSeverity,
    WeChatWorkAdapter,
)
from services.telegram_adapter import TelegramAdapter

logger = logging.getLogger(__name__)


class AlertPushService:
    """告警推送服务（静态方法模式）"""

    @classmethod
    async def push(
        cls,
        alert_id: str,
        result: dict,
        snapshot_path: Optional[str] = None,
    ) -> None:
        """推送告警到已启用的通道（fire-and-log，不抛异常）"""
        violation_type = result.get("violation_type", "unknown")
        confidence = result.get("confidence", 0.0)
        description = result.get("description", "")

        # 构建图片 URL
        image_url = None
        if snapshot_path:
            image_url = (
                f"{ServerConfig.PUBLIC_BASE_URL}/api/image-proxy/{snapshot_path}"
            )

        # 构建推送消息文本
        alert_link = f"{ServerConfig.PUBLIC_BASE_URL}/alerts/{alert_id}"
        message_text = (
            f"[Vistrat] {violation_type}\n"
            f"Confidence: {confidence:.0%}\n"
            f"{description}\n\n"
            f"Detail: {alert_link}"
        )

        # 企业微信推送
        if AlertConfig.ENABLE_WECHAT and AlertConfig.WECHAT_WEBHOOK_URL:
            try:
                adapter = WeChatWorkAdapter(AlertConfig.WECHAT_WEBHOOK_URL)
                msg = NotificationMessage(
                    title=f"Vistrat: {violation_type}",
                    content=f"{description}\n\n[View alert]({alert_link})",
                    severity=_map_severity(result.get("severity", "warning")),
                    timestamp=time.time(),
                    extra_data={
                        "alert_id": alert_id,
                        "confidence": f"{confidence:.0%}",
                        "violation_type": violation_type,
                    },
                )
                await adapter.send(msg)
            except Exception as e:
                logger.warning(f"企业微信推送失败（alert_id={alert_id}）: {e}")

        # Telegram 推送
        if AlertConfig.ENABLE_TELEGRAM and AlertConfig.TELEGRAM_BOT_TOKEN:
            try:
                adapter = TelegramAdapter(
                    AlertConfig.TELEGRAM_BOT_TOKEN, AlertConfig.TELEGRAM_CHAT_ID
                )
                await adapter.send_alert_with_buttons(
                    alert_id=alert_id,
                    message=message_text,
                    image_url=image_url,
                )
            except Exception as e:
                logger.warning(f"Telegram 推送失败（alert_id={alert_id}）: {e}")


def _map_severity(level: str) -> NotificationSeverity:
    """映射告警级别到通知严重度"""
    mapping = {
        "info": NotificationSeverity.INFO,
        "warning": NotificationSeverity.WARNING,
        "error": NotificationSeverity.ERROR,
        "critical": NotificationSeverity.CRITICAL,
    }
    return mapping.get(level, NotificationSeverity.WARNING)
