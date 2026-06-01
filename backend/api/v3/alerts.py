"""v3 告警管理 API"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from models.alert import AlertStatusEnum
from services.alert_service_v3 import AlertServiceV3

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["v3-告警管理"])


class UpdateStatusRequest(BaseModel):
    """更新告警状态请求"""
    new_status: AlertStatusEnum = Field(..., description="新状态")
    created_at: datetime = Field(..., description="告警创建时间（分区键）")
    feedback_by: Optional[str] = Field(None, description="反馈人")


@router.get("/")
async def list_alerts(
    stream_id: Optional[str] = Query(None, description="视频流ID"),
    status: Optional[str] = Query(None, description="告警状态过滤"),
    limit: int = Query(50, ge=1, le=200, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """查询告警列表"""
    try:
        alerts = await AlertServiceV3.get_alerts(
            stream_id=stream_id, status=status, limit=limit, offset=offset
        )
        return {"items": alerts, "total": len(alerts)}
    except Exception as e:
        logger.error(f"查询告警列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询告警列表失败: {e}")


@router.get("/statistics/feedback")
async def feedback_statistics():
    """反馈统计"""
    try:
        stats = await AlertServiceV3.get_feedback_statistics()
        return stats
    except Exception as e:
        logger.error(f"查询反馈统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询反馈统计失败: {e}")


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """查询单个告警详情"""
    try:
        alert = await AlertServiceV3.get_alert(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="告警不存在")
        return alert
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询告警详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询告警详情失败: {e}")


@router.patch("/{alert_id}/status")
async def update_alert_status(alert_id: str, body: UpdateStatusRequest):
    """更新告警状态"""
    try:
        success = await AlertServiceV3.update_alert_status(
            alert_id=alert_id,
            created_at=body.created_at,
            new_status=body.new_status,
            feedback_by=body.feedback_by,
        )
        if not success:
            raise HTTPException(status_code=404, detail="告警不存在")
        return {"status": "updated", "new_status": body.new_status.value}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新告警状态失败: {e}")
