"""Alert push notification tests (ALERT-02)"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from services.notification_adapters import NotificationAdapter


class TestAlertPushService:
    @pytest.mark.asyncio
    async def test_push_calls_wechat_when_enabled(self):
        with patch("services.alert_push_service.AlertConfig") as mock_config:
            mock_config.ENABLE_WECHAT = True
            mock_config.WECHAT_WEBHOOK_URL = "https://example.com/webhook"
            mock_config.ENABLE_TELEGRAM = False
            mock_config.TELEGRAM_BOT_TOKEN = ""

            with patch("services.alert_push_service.WeChatWorkAdapter") as mock_wechat:
                mock_adapter = AsyncMock()
                mock_adapter.send = AsyncMock(return_value=True)
                mock_wechat.return_value = mock_adapter

                from services.alert_push_service import AlertPushService
                await AlertPushService.push(
                    alert_id="test-id",
                    result={"violation_type": "no_helmet", "confidence": 0.9, "description": "test"},
                )

                mock_adapter.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_calls_telegram_when_enabled(self):
        with patch("services.alert_push_service.AlertConfig") as mock_config:
            mock_config.ENABLE_WECHAT = False
            mock_config.WECHAT_WEBHOOK_URL = ""
            mock_config.ENABLE_TELEGRAM = True
            mock_config.TELEGRAM_BOT_TOKEN = "bot-token"
            mock_config.TELEGRAM_CHAT_ID = "chat-id"

            with patch("services.alert_push_service.TelegramAdapter") as mock_tg:
                mock_adapter = AsyncMock()
                mock_adapter.send_alert_with_buttons = AsyncMock(return_value=True)
                mock_tg.return_value = mock_adapter

                from services.alert_push_service import AlertPushService
                await AlertPushService.push(
                    alert_id="test-id",
                    result={"violation_type": "no_helmet", "confidence": 0.9, "description": "test"},
                )

                mock_adapter.send_alert_with_buttons.assert_called_once()

    @pytest.mark.asyncio
    async def test_push_failure_does_not_raise(self):
        """Fire-and-log: push failure should not propagate exceptions"""
        with patch("services.alert_push_service.AlertConfig") as mock_config:
            mock_config.ENABLE_WECHAT = True
            mock_config.WECHAT_WEBHOOK_URL = "https://example.com/webhook"
            mock_config.ENABLE_TELEGRAM = True
            mock_config.TELEGRAM_BOT_TOKEN = "bot-token"
            mock_config.TELEGRAM_CHAT_ID = "chat-id"

            with patch("services.alert_push_service.WeChatWorkAdapter") as mock_wechat:
                mock_wechat.return_value.send = AsyncMock(side_effect=Exception("boom"))
                with patch("services.alert_push_service.TelegramAdapter") as mock_tg:
                    mock_tg.return_value.send_alert_with_buttons = AsyncMock(
                        side_effect=Exception("boom")
                    )

                    from services.alert_push_service import AlertPushService
                    # Should NOT raise
                    await AlertPushService.push(
                        alert_id="test-id",
                        result={"violation_type": "test", "confidence": 0.5, "description": ""},
                    )


class TestTelegramAdapter:
    def test_inherits_notification_adapter(self):
        from services.telegram_adapter import TelegramAdapter
        assert issubclass(TelegramAdapter, NotificationAdapter)

    def test_has_send_alert_with_buttons(self):
        from services.telegram_adapter import TelegramAdapter
        adapter = TelegramAdapter(bot_token="test", chat_id="123")
        assert hasattr(adapter, "send_alert_with_buttons")

    def test_has_answer_callback_query(self):
        from services.telegram_adapter import TelegramAdapter
        adapter = TelegramAdapter(bot_token="test", chat_id="123")
        assert hasattr(adapter, "answer_callback_query")

    def test_base_url_format(self):
        from services.telegram_adapter import TelegramAdapter
        adapter = TelegramAdapter(bot_token="mytoken", chat_id="123")
        assert adapter.base_url == "https://api.telegram.org/botmytoken"
