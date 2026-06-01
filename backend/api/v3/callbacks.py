"""v3 告警回调端点 -- Telegram / 企业微信"""

import logging
from typing import Optional

from fastapi import APIRouter, Request

from models.alert import AlertStatusEnum
from services.alert_service_v3 import AlertServiceV3

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/callbacks", tags=["v3-告警回调"])


@router.post("/telegram")
async def telegram_callback(request: Request):
    """接收 Telegram callback_query Webhook"""
    try:
        data = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid json"}

    callback_query = data.get("callback_query")
    if not callback_query:
        return {"status": "ignored", "reason": "no callback_query"}

    cb_data = callback_query.get("data", "")
    callback_query_id = callback_query.get("id")

    # 解析 action:alert_id 格式
    if ":" not in cb_data:
        return {"status": "ignored", "reason": "invalid callback data format"}

    action, alert_id = cb_data.split(":", 1)

    # 映射 action 到状态
    status_map = {
        "confirm": AlertStatusEnum.CONFIRMED,
        "dismiss": AlertStatusEnum.DISMISSED,
    }
    new_status = status_map.get(action)
    if new_status is None:
        return {"status": "ignored", "reason": f"unknown action: {action}"}

    # 查询告警获取 created_at（分区表需要）
    alert = await AlertServiceV3.get_alert(alert_id)
    if alert is None:
        return {"status": "error", "reason": "alert not found"}

    from datetime import datetime
    created_at = datetime.fromisoformat(alert["created_at"])

    # 更新状态
    feedback_by = None
    from_user = callback_query.get("from", {})
    if from_user:
        feedback_by = from_user.get("username") or str(from_user.get("id", ""))

    try:
        await AlertServiceV3.update_alert_status(
            alert_id=alert_id,
            created_at=created_at,
            new_status=new_status,
            feedback_by=feedback_by,
        )
    except ValueError as e:
        logger.warning(f"Telegram 回调状态转换失败: {e}")
        return {"status": "error", "reason": str(e)}

    # 回复 callback_query
    try:
        from config.settings import AlertConfig
        from services.telegram_adapter import TelegramAdapter
        if AlertConfig.TELEGRAM_BOT_TOKEN:
            adapter = TelegramAdapter(
                AlertConfig.TELEGRAM_BOT_TOKEN, AlertConfig.TELEGRAM_CHAT_ID
            )
            await adapter.answer_callback_query(
                callback_query_id, f"Alert {action}ed"
            )
    except Exception as e:
        logger.warning(f"Telegram 回复回调失败: {e}")

    return {"status": "ok", "action": action, "alert_id": alert_id}


@router.post("/wechat")
async def wechat_callback(request: Request):
    """
    企业微信回调端点

    重要限制：企业微信群机器人 Webhook 只能发送消息，不能接收回调。
    此端点仅在配置了企业微信自建应用（非群机器人）时才能工作。
    """
    try:
        data = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid json"}

    if not data:
        return {"status": "ignored", "reason": "empty body"}

    # 解析 template_card_event
    event = data.get("template_card_event")
    if not event:
        return {"status": "ignored", "reason": "unsupported callback format"}

    key = event.get("key", "")
    if ":" not in key:
        return {"status": "ignored", "reason": "invalid key format"}

    action, alert_id = key.split(":", 1)

    status_map = {
        "confirm": AlertStatusEnum.CONFIRMED,
        "dismiss": AlertStatusEnum.DISMISSED,
    }
    new_status = status_map.get(action)
    if new_status is None:
        return {"status": "ignored", "reason": f"unknown action: {action}"}

    # 查询告警获取 created_at
    alert = await AlertServiceV3.get_alert(alert_id)
    if alert is None:
        return {"status": "error", "reason": "alert not found"}

    from datetime import datetime
    created_at = datetime.fromisoformat(alert["created_at"])

    feedback_by = event.get("user_id")

    try:
        await AlertServiceV3.update_alert_status(
            alert_id=alert_id,
            created_at=created_at,
            new_status=new_status,
            feedback_by=feedback_by,
        )
    except ValueError as e:
        logger.warning(f"企业微信回调状态转换失败: {e}")
        return {"status": "error", "reason": str(e)}

    return {"status": "ok", "action": action, "alert_id": alert_id}
