"""v3.0 告警服务 -- 告警生成、状态机转换、反馈统计"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.orm.attributes import flag_modified

from config.settings import MediaMTXConfig
from database.connection import DatabaseManager
from models.alert import AlertDB, AlertStatusEnum, AlertResponse

logger = logging.getLogger(__name__)

# 片段生成窗口（秒）：从 MediaMTXConfig 读取，保持与 ClipService 的默认值一致
CLIP_PRE_SECONDS = MediaMTXConfig.CLIP_PRE_SECONDS
CLIP_POST_SECONDS = MediaMTXConfig.CLIP_POST_SECONDS
# 调度延迟：等 post 窗口落盘 + 1s 缓冲
CLIP_SCHEDULE_DELAY_SECONDS = CLIP_POST_SECONDS + 1


class AlertServiceV3:
    """告警生命周期管理"""

    # 状态机：合法转换定义
    VALID_TRANSITIONS = {
        AlertStatusEnum.PENDING: {AlertStatusEnum.CONFIRMED, AlertStatusEnum.DISMISSED},
        AlertStatusEnum.CONFIRMED: {AlertStatusEnum.RESOLVED},
        AlertStatusEnum.DISMISSED: {AlertStatusEnum.RESOLVED},
        AlertStatusEnum.RESOLVED: set(),
    }

    @classmethod
    async def create_alert(
        cls,
        stream_id: str,
        task_id: str,
        result: dict,
        snapshot_path: Optional[str] = None,
    ) -> dict:
        """高置信度违规时创建告警，异步推送"""
        alert = AlertDB(
            stream_id=UUID(stream_id),
            task_id=UUID(task_id) if task_id else None,
            level=result.get("severity", "warning"),
            status=AlertStatusEnum.PENDING,
            result=result,
            snapshot_path=snapshot_path,
            message=result.get("description", ""),
        )

        async with DatabaseManager.get_session() as session:
            session.add(alert)
            await session.flush()
            # 分区表：flush 后获取 id 和 created_at
            alert_id = str(alert.id)
            alert_created_at = alert.created_at

        # 双写 ES video_alerts（老 /api/alerts/search 走 ES；失败绝不影响 PG 主链路）
        # doc id = alert_id（UUID 字符串），与 update_alert_fields 的 id 约定一致
        try:
            await cls._index_alert_to_es(alert, result, alert_id, alert_created_at)
        except Exception as e:
            logger.warning(
                f"v3 告警双写 ES 失败（PG 已落库） alert_id={alert_id}: {e}"
            )

        # 异步推送（不阻塞分析管线）
        try:
            from services.alert_push_service import AlertPushService
            asyncio.create_task(
                AlertPushService.push(alert_id, result, snapshot_path)
            )
        except Exception as e:
            logger.warning(f"告警推送任务创建失败: {e}")

        # 调度视频片段生成任务（Week 3B 新增；失败绝不阻塞主告警链路）
        try:
            cls._schedule_clip_generation(
                alert_id=alert_id,
                stream_id=stream_id,
                trigger_ts=alert_created_at,
            )
        except Exception as e:
            logger.error(f"调度 clip 任务失败 alert_id={alert_id}: {e}")

        logger.info(f"告警已创建: alert_id={alert_id}, stream={stream_id}")
        return {"alert_id": alert_id, "status": "pending"}

    @classmethod
    async def _index_alert_to_es(
        cls,
        alert: AlertDB,
        result: dict,
        alert_id: str,
        alert_created_at: datetime,
    ) -> None:
        """把告警铺平为 ES doc 并调 elasticsearch_service.index_alert 双写。

        AlertDB 本身只有 level/status/result/snapshot_path/message 等列；
        前端老 API /api/alerts/search 读的 stream_name/violation_type/
        confidence/description/image_url/detection_objects/image_size 等
        字段存在 result JSONB 里，这里铺平到顶层 source 字段以兼容老查询。
        """
        from services.elasticsearch_service import elasticsearch_service

        result = result or {}
        # created_at 兼容 datetime / None
        created_iso = (
            alert_created_at.isoformat() if alert_created_at else None
        )
        alert_doc = {
            # 主键（与 update_alert_fields doc id 一致）
            "id": alert_id,
            # 基础字段
            "stream_id": str(alert.stream_id) if alert.stream_id else None,
            "task_id": str(alert.task_id) if alert.task_id else None,
            "level": alert.level,
            "status": alert.status.value if hasattr(alert.status, "value") else alert.status,
            "message": alert.message,
            "snapshot_path": alert.snapshot_path,
            "created_at": created_iso,
            # 来源标记：区分 v3 与老告警路径
            "source": "v3",
            # 业务字段（从 result JSONB 铺平到顶层，兼容老 API）
            "violation_type": result.get("violation_type"),
            "severity": result.get("severity", alert.level),
            "confidence": result.get("confidence"),
            "description": result.get("description", alert.message or ""),
            "image_url": result.get("image_url") or alert.snapshot_path,
            "detection_objects": result.get("detection_objects") or [],
            "image_size": result.get("image_size"),
            "stream_name": result.get("stream_name"),
            "camera_name": result.get("camera_name") or result.get("stream_name"),
            "algorithm_name": result.get("algorithm_name") or result.get("template_name"),
            "template_name": result.get("template_name"),
            "analysis_type": result.get("analysis_type", "stream_analysis"),
            "detection_details": result.get("detection_details", {}),
            # clip 字段初始值（Week 3B 异步调度完成后由 update_alert_fields 更新）
            "clip_url": getattr(alert, "clip_url", None),
            "clip_status": getattr(alert, "clip_status", "pending") or "pending",
            # 保留原始 result 便于调试
            "result": result,
        }

        await elasticsearch_service.index_alert(alert_doc)

    @classmethod
    def _schedule_clip_generation(
        cls,
        alert_id: str,
        stream_id: str,
        trigger_ts: datetime,
    ) -> None:
        """通过 APScheduler 延迟调度 clip 生成任务

        延迟原因：需要等 post_seconds 窗口内的视频落盘，否则截取到空帧。
        使用全局 SchedulerService 单例（与其他后台任务共享调度器）。
        """
        from services.scheduler_service import SchedulerService

        run_at = datetime.now(timezone.utc) + timedelta(
            seconds=CLIP_SCHEDULE_DELAY_SECONDS
        )
        scheduler = SchedulerService.get_instance()
        scheduler.add_job(
            _run_clip_job,
            trigger="date",
            run_date=run_at,
            args=[alert_id, stream_id, trigger_ts],
            id=f"clip_{alert_id}",
            replace_existing=True,
        )
        logger.info(
            f"已调度 clip 生成任务: alert_id={alert_id}, run_at={run_at.isoformat()}"
        )

    @classmethod
    async def update_alert_clip(
        cls,
        alert_id: str,
        clip_url: Optional[str],
        clip_status: str,
    ) -> bool:
        """更新告警的 clip_url / clip_status（Week 3B 新增）

        分区表无 created_at 时按 id 全表扫描（由 PG 剪枝），写入量小可接受。
        """
        if clip_status not in ("pending", "ready", "failed", "skipped"):
            raise ValueError(f"非法的 clip_status: {clip_status}")

        async with DatabaseManager.get_session() as session:
            stmt = (
                update(AlertDB)
                .where(AlertDB.id == UUID(alert_id))
                .values(clip_url=clip_url, clip_status=clip_status)
            )
            result = await session.execute(stmt)
            pg_ok = result.rowcount > 0

        # PG 写成功后 best-effort 同步到 ES（老 /api/alerts/search 走 ES）
        # ES 文档 id 约定为 AlertDB.id；若 v3 链路尚未写 ES 则 update miss，属预期
        if pg_ok:
            try:
                from services.elasticsearch_service import elasticsearch_service
                await elasticsearch_service.update_alert_fields(
                    alert_id=alert_id,
                    fields={"clip_url": clip_url, "clip_status": clip_status},
                )
            except Exception as e:
                logger.warning(
                    f"ES 同步 clip 字段失败（PG 已写成功） alert_id={alert_id}: {e}"
                )

        return pg_ok

    @classmethod
    async def update_alert_status(
        cls,
        alert_id: str,
        created_at: datetime,
        new_status: AlertStatusEnum,
        feedback_by: Optional[str] = None,
    ) -> bool:
        """更新告警状态（含状态机校验和反馈数据沉淀）"""
        async with DatabaseManager.get_session() as session:
            # 分区表复合 PK 查询
            stmt = select(AlertDB).where(
                AlertDB.id == UUID(alert_id),
                AlertDB.created_at == created_at,
            )
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()

            if alert is None:
                return False

            # 状态机校验
            current = alert.status
            allowed = cls.VALID_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                raise ValueError(
                    f"非法状态转换: {current.value} -> {new_status.value}"
                )

            # 更新状态
            alert.status = new_status

            # 反馈数据沉淀到 result JSONB
            existing_result = alert.result or {}
            existing_result["feedback_at"] = datetime.now(timezone.utc).isoformat()
            existing_result["feedback_by"] = feedback_by
            existing_result["feedback_action"] = new_status.value
            alert.result = existing_result
            flag_modified(alert, "result")

        logger.info(
            f"告警状态更新: alert_id={alert_id}, {current.value} -> {new_status.value}"
        )
        return True

    @classmethod
    async def get_alert(
        cls, alert_id: str, created_at: Optional[datetime] = None
    ) -> Optional[dict]:
        """查询单个告警详情"""
        async with DatabaseManager.get_session() as session:
            if created_at:
                stmt = select(AlertDB).where(
                    AlertDB.id == UUID(alert_id),
                    AlertDB.created_at == created_at,
                )
            else:
                # 无 created_at 时按 id 查询（可能跨分区较慢）
                stmt = select(AlertDB).where(AlertDB.id == UUID(alert_id))
            result = await session.execute(stmt)
            alert = result.scalar_one_or_none()
            if alert is None:
                return None
            return _alert_to_dict(alert)

    @classmethod
    async def get_alerts(
        cls,
        stream_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """查询告警列表"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AlertDB).order_by(AlertDB.created_at.desc())
            if stream_id:
                stmt = stmt.where(AlertDB.stream_id == UUID(stream_id))
            if status:
                stmt = stmt.where(AlertDB.status == AlertStatusEnum(status))
            stmt = stmt.limit(limit).offset(offset)
            result = await session.execute(stmt)
            alerts = result.scalars().all()
            return [_alert_to_dict(a) for a in alerts]

    @classmethod
    async def get_feedback_statistics(cls) -> dict:
        """按状态分组统计"""
        async with DatabaseManager.get_session() as session:
            stmt = select(
                AlertDB.status, func.count(AlertDB.id)
            ).group_by(AlertDB.status)
            result = await session.execute(stmt)
            rows = result.all()

        stats = {s.value: 0 for s in AlertStatusEnum}
        for status_enum, count in rows:
            stats[status_enum.value] = count
        return stats


async def _run_clip_job(
    alert_id: str,
    stream_id: str,
    trigger_ts: datetime,
) -> None:
    """APScheduler 执行体：调用 ClipService 生成片段，更新 DB 并广播 WS

    整块 try/except 包住 — 失败只写日志，不让 APScheduler 记 error。
    ClipService 未就绪（Week 3A 未合入）时捕获 ImportError，状态置 failed。
    """
    try:
        try:
            from services.clip_service import ClipService  # type: ignore
        except ImportError:
            logger.warning(
                f"ClipService 未就绪，跳过片段生成 alert_id={alert_id}"
            )
            await AlertServiceV3.update_alert_clip(
                alert_id=alert_id, clip_url=None, clip_status="skipped"
            )
            await _broadcast_clip_event(
                event_type="clip_failed", alert_id=alert_id, clip_url=None
            )
            return

        clip_url = await ClipService().create_alert_clip(
            alert_id=alert_id,
            stream_id=stream_id,
            trigger_ts=trigger_ts,
            pre_seconds=CLIP_PRE_SECONDS,
            post_seconds=CLIP_POST_SECONDS,
        )

        if clip_url:
            await AlertServiceV3.update_alert_clip(
                alert_id=alert_id, clip_url=clip_url, clip_status="ready"
            )
            await _broadcast_clip_event(
                event_type="clip_ready", alert_id=alert_id, clip_url=clip_url
            )
            logger.info(f"片段生成成功: alert_id={alert_id} url={clip_url}")
        else:
            await AlertServiceV3.update_alert_clip(
                alert_id=alert_id, clip_url=None, clip_status="failed"
            )
            await _broadcast_clip_event(
                event_type="clip_failed", alert_id=alert_id, clip_url=None
            )
            logger.warning(f"片段生成失败（ClipService 返回 None）: alert_id={alert_id}")

    except Exception as e:
        logger.error(f"片段生成任务异常 alert_id={alert_id}: {e}", exc_info=True)
        # 尽量把状态落到 failed，避免永远卡 pending
        try:
            await AlertServiceV3.update_alert_clip(
                alert_id=alert_id, clip_url=None, clip_status="failed"
            )
            await _broadcast_clip_event(
                event_type="clip_failed", alert_id=alert_id, clip_url=None
            )
        except Exception as inner:
            logger.error(f"更新失败状态也出错: {inner}")


async def _broadcast_clip_event(
    event_type: str,
    alert_id: str,
    clip_url: Optional[str],
) -> None:
    """复用 core.alert_service.AlertService 的 WS 连接广播 clip 事件

    沿用现有通道（/alerts WebSocket），通过 type 字段区分新事件类型。
    发送失败不抛。
    """
    import json as _json
    try:
        from core.alert_service import AlertService as _AlertWS
        payload = {
            "type": event_type,  # "clip_ready" 或 "clip_failed"
            "alert_id": alert_id,
            "clip_url": clip_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        message = _json.dumps(payload, ensure_ascii=False)
        disconnected = set()
        for ws in list(_AlertWS._connections):
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.debug(f"WS 发送 clip 事件失败: {e}")
                disconnected.add(ws)
        _AlertWS._connections -= disconnected
    except Exception as e:
        logger.warning(f"广播 clip 事件失败 alert_id={alert_id}: {e}")


def _alert_to_dict(alert: AlertDB) -> dict:
    """AlertDB -> dict"""
    return {
        "id": str(alert.id),
        "stream_id": str(alert.stream_id),
        "task_id": str(alert.task_id) if alert.task_id else None,
        "level": alert.level,
        "status": alert.status.value if isinstance(alert.status, AlertStatusEnum) else alert.status,
        "result": alert.result,
        "snapshot_path": alert.snapshot_path,
        "message": alert.message,
        "project_id": alert.project_id if hasattr(alert, "project_id") else None,
        "clip_url": getattr(alert, "clip_url", None),
        "clip_status": getattr(alert, "clip_status", "pending"),
        "created_at": alert.created_at.isoformat() if alert.created_at else None,
        "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
    }
