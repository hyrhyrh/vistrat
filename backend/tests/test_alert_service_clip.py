"""Week 3B: AlertServiceV3 的 clip 异步触发测试

覆盖点：
  1. ClipService 返回 URL -> DB 更新为 ready + 广播 clip_ready
  2. ClipService 返回 None -> DB 更新为 failed + 广播 clip_failed
  3. ClipService 抛异常 -> 不冒泡到主告警链路；状态退到 failed
  4. create_alert 调用后会通过 SchedulerService 调度 clip 任务
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# 让导入可解析 backend 顶层包
_BACKEND = Path(__file__).resolve().parent.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def sample_alert_id():
    return str(uuid4())


@pytest.fixture
def sample_stream_id():
    return str(uuid4())


@pytest.fixture
def sample_trigger_ts():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------
# 1. create_alert 成功后会调度 clip 任务
# ---------------------------------------------------------------------
class TestScheduleClipOnCreate:
    @pytest.mark.asyncio
    async def test_create_alert_schedules_clip_job(self):
        from services import alert_service_v3 as mod

        sample_stream = str(uuid4())
        sample_task = str(uuid4())
        sample_result = {
            "has_violation": True,
            "confidence": 0.9,
            "severity": "warning",
            "description": "测试告警",
            "violation_type": "test",
        }

        with patch.object(mod, "DatabaseManager") as mock_db, \
             patch.object(mod.AlertServiceV3, "_schedule_clip_generation") as mock_sched, \
             patch("services.alert_push_service.AlertPushService.push", new=AsyncMock()), \
             patch.object(mod.asyncio, "create_task"):

            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
            mock_session.add.side_effect = capture_add

            await mod.AlertServiceV3.create_alert(
                stream_id=sample_stream,
                task_id=sample_task,
                result=sample_result,
            )

            mock_sched.assert_called_once()
            kwargs = mock_sched.call_args.kwargs
            assert "alert_id" in kwargs
            assert kwargs["stream_id"] == sample_stream

    @pytest.mark.asyncio
    async def test_schedule_failure_does_not_break_create(self):
        """调度器抛异常时 create_alert 仍成功返回"""
        from services import alert_service_v3 as mod

        sample_stream = str(uuid4())
        sample_task = str(uuid4())
        sample_result = {"description": "x", "severity": "warning"}

        with patch.object(mod, "DatabaseManager") as mock_db, \
             patch.object(
                 mod.AlertServiceV3,
                 "_schedule_clip_generation",
                 side_effect=RuntimeError("scheduler 挂了"),
             ), \
             patch("services.alert_push_service.AlertPushService.push", new=AsyncMock()), \
             patch.object(mod.asyncio, "create_task"):

            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
            mock_session.add.side_effect = capture_add

            result = await mod.AlertServiceV3.create_alert(
                stream_id=sample_stream,
                task_id=sample_task,
                result=sample_result,
            )
            assert result["status"] == "pending"


# ---------------------------------------------------------------------
# 2. _run_clip_job 三条路径
# ---------------------------------------------------------------------
class TestRunClipJob:
    @pytest.mark.asyncio
    async def test_clip_success_updates_ready_and_broadcasts(
        self, sample_alert_id, sample_stream_id, sample_trigger_ts
    ):
        from services import alert_service_v3 as mod

        fake_clip_service = MagicMock()
        fake_clip_service.create_alert_clip = AsyncMock(
            return_value="http://minio/clips/abc.mp4"
        )
        fake_module = MagicMock()
        fake_module.ClipService = MagicMock(return_value=fake_clip_service)

        with patch.dict(sys.modules, {"services.clip_service": fake_module}), \
             patch.object(
                 mod.AlertServiceV3, "update_alert_clip", new=AsyncMock(return_value=True)
             ) as mock_update, \
             patch.object(mod, "_broadcast_clip_event", new=AsyncMock()) as mock_bc:

            await mod._run_clip_job(sample_alert_id, sample_stream_id, sample_trigger_ts)

            mock_update.assert_awaited_once_with(
                alert_id=sample_alert_id,
                clip_url="http://minio/clips/abc.mp4",
                clip_status="ready",
            )
            mock_bc.assert_awaited_once()
            assert mock_bc.call_args.kwargs["event_type"] == "clip_ready"
            assert mock_bc.call_args.kwargs["clip_url"] == "http://minio/clips/abc.mp4"

    @pytest.mark.asyncio
    async def test_clip_returns_none_marks_failed(
        self, sample_alert_id, sample_stream_id, sample_trigger_ts
    ):
        from services import alert_service_v3 as mod

        fake_clip_service = MagicMock()
        fake_clip_service.create_alert_clip = AsyncMock(return_value=None)
        fake_module = MagicMock()
        fake_module.ClipService = MagicMock(return_value=fake_clip_service)

        with patch.dict(sys.modules, {"services.clip_service": fake_module}), \
             patch.object(
                 mod.AlertServiceV3, "update_alert_clip", new=AsyncMock(return_value=True)
             ) as mock_update, \
             patch.object(mod, "_broadcast_clip_event", new=AsyncMock()) as mock_bc:

            await mod._run_clip_job(sample_alert_id, sample_stream_id, sample_trigger_ts)

            mock_update.assert_awaited_once_with(
                alert_id=sample_alert_id,
                clip_url=None,
                clip_status="failed",
            )
            assert mock_bc.call_args.kwargs["event_type"] == "clip_failed"

    @pytest.mark.asyncio
    async def test_clip_exception_does_not_raise(
        self, sample_alert_id, sample_stream_id, sample_trigger_ts
    ):
        from services import alert_service_v3 as mod

        fake_clip_service = MagicMock()
        fake_clip_service.create_alert_clip = AsyncMock(side_effect=RuntimeError("boom"))
        fake_module = MagicMock()
        fake_module.ClipService = MagicMock(return_value=fake_clip_service)

        with patch.dict(sys.modules, {"services.clip_service": fake_module}), \
             patch.object(
                 mod.AlertServiceV3, "update_alert_clip", new=AsyncMock(return_value=True)
             ) as mock_update, \
             patch.object(mod, "_broadcast_clip_event", new=AsyncMock()):

            # 不应抛，外层 try/except 兜底
            await mod._run_clip_job(sample_alert_id, sample_stream_id, sample_trigger_ts)

            # 异常路径仍会尝试把状态写成 failed
            mock_update.assert_awaited()
            args = mock_update.call_args.kwargs
            assert args["clip_status"] == "failed"

    @pytest.mark.asyncio
    async def test_clip_service_missing_marks_skipped(
        self, sample_alert_id, sample_stream_id, sample_trigger_ts
    ):
        """Week 3A 未合入时，ClipService 模块不存在 -> skipped"""
        from services import alert_service_v3 as mod

        # 强制 ImportError
        with patch.dict(sys.modules, {"services.clip_service": None}), \
             patch.object(
                 mod.AlertServiceV3, "update_alert_clip", new=AsyncMock(return_value=True)
             ) as mock_update, \
             patch.object(mod, "_broadcast_clip_event", new=AsyncMock()) as mock_bc:

            await mod._run_clip_job(sample_alert_id, sample_stream_id, sample_trigger_ts)

            mock_update.assert_awaited_once_with(
                alert_id=sample_alert_id,
                clip_url=None,
                clip_status="skipped",
            )
            assert mock_bc.call_args.kwargs["event_type"] == "clip_failed"


# ---------------------------------------------------------------------
# 3. update_alert_clip 参数校验
# ---------------------------------------------------------------------
class TestUpdateAlertClip:
    @pytest.mark.asyncio
    async def test_invalid_status_raises(self, sample_alert_id):
        from services.alert_service_v3 import AlertServiceV3

        with pytest.raises(ValueError):
            await AlertServiceV3.update_alert_clip(
                alert_id=sample_alert_id, clip_url=None, clip_status="bogus"
            )

    @pytest.mark.asyncio
    async def test_update_calls_session_execute(self, sample_alert_id):
        from services import alert_service_v3 as mod

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch.object(mod, "DatabaseManager") as mock_db:
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            ok = await mod.AlertServiceV3.update_alert_clip(
                alert_id=sample_alert_id,
                clip_url="http://x/y.mp4",
                clip_status="ready",
            )
            assert ok is True
            mock_session.execute.assert_awaited_once()
