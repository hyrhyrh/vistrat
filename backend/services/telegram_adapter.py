"""Telegram Bot API 适配器"""

import json
import logging
from typing import Optional

import httpx

from config.settings import AlertConfig
from services.notification_adapters import NotificationAdapter, NotificationMessage

logger = logging.getLogger(__name__)


class TelegramAdapter(NotificationAdapter):
    """Telegram Bot 推送适配器，支持 InlineKeyboard 回调按钮"""

    def __init__(self, bot_token: str, chat_id: str):
        super().__init__()
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.chat_id = chat_id

    async def send(self, message: NotificationMessage) -> bool:
        """发送 Markdown 格式消息"""
        try:
            text = self._format_message(message)
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }
            async with httpx.AsyncClient(timeout=AlertConfig.PUSH_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/sendMessage", json=payload
                )
                if resp.status_code == 200 and resp.json().get("ok"):
                    self.total_sent += 1
                    self.last_send_time = __import__("time").time()
                    logger.info(f"Telegram 消息发送成功: {message.title}")
                    return True
                else:
                    self.total_failed += 1
                    logger.warning(f"Telegram 消息发送失败: {resp.text}")
                    return False
        except Exception as e:
            self.total_failed += 1
            logger.error(f"Telegram 消息发送异常: {e}")
            return False

    async def send_alert_with_buttons(
        self,
        alert_id: str,
        message: str,
        image_url: Optional[str] = None,
    ) -> bool:
        """发送带 InlineKeyboard 按钮的告警消息"""
        try:
            inline_keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "Confirm", "callback_data": f"confirm:{alert_id}"},
                        {"text": "Dismiss", "callback_data": f"dismiss:{alert_id}"},
                    ]
                ]
            }

            # 如果有图片，先发图片再发按钮消息
            if image_url:
                photo_payload = {
                    "chat_id": self.chat_id,
                    "photo": image_url,
                    "caption": message[:1024],  # Telegram caption 限制
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps(inline_keyboard),
                }
                async with httpx.AsyncClient(timeout=AlertConfig.PUSH_TIMEOUT) as client:
                    resp = await client.post(
                        f"{self.base_url}/sendPhoto", json=photo_payload
                    )
            else:
                payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "reply_markup": json.dumps(inline_keyboard),
                }
                async with httpx.AsyncClient(timeout=AlertConfig.PUSH_TIMEOUT) as client:
                    resp = await client.post(
                        f"{self.base_url}/sendMessage", json=payload
                    )

            if resp.status_code == 200 and resp.json().get("ok"):
                self.total_sent += 1
                self.last_send_time = __import__("time").time()
                logger.info(f"Telegram 告警消息发送成功: alert_id={alert_id}")
                return True
            else:
                self.total_failed += 1
                logger.warning(f"Telegram 告警消息发送失败: {resp.text}")
                return False
        except Exception as e:
            self.total_failed += 1
            logger.error(f"Telegram 告警消息发送异常: {e}")
            return False

    async def answer_callback_query(
        self, callback_query_id: str, text: str
    ) -> bool:
        """回复 Telegram callback_query"""
        try:
            payload = {
                "callback_query_id": callback_query_id,
                "text": text,
            }
            async with httpx.AsyncClient(timeout=AlertConfig.PUSH_TIMEOUT) as client:
                resp = await client.post(
                    f"{self.base_url}/answerCallbackQuery", json=payload
                )
                return resp.status_code == 200 and resp.json().get("ok", False)
        except Exception as e:
            logger.error(f"Telegram 回复回调异常: {e}")
            return False

    @staticmethod
    def _format_message(message: NotificationMessage) -> str:
        """格式化通知消息为 Markdown"""
        from datetime import datetime

        time_str = datetime.fromtimestamp(message.timestamp).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        return (
            f"*{message.title}*\n\n"
            f"Level: `{message.severity.value}`\n"
            f"Time: {time_str}\n"
            f"Source: {message.source}\n\n"
            f"{message.content}"
        )
