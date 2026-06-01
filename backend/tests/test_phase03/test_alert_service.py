"""AlertServiceV3 tests (ALERT-01, ALERT-03, ALERT-04)"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone

from models.alert import AlertStatusEnum


# ALERT-01: High confidence result generates pending alert
class TestCreateAlert:
    @pytest.mark.asyncio
    async def test_create_alert_returns_pending(self, sample_alert_result, sample_stream_id, sample_task_id):
        with patch("services.alert_service_v3.DatabaseManager") as mock_db:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            # Patch the alert so flush populates id/created_at
            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
            mock_session.add.side_effect = capture_add

            with patch("services.alert_service_v3.asyncio.create_task"):
                from services.alert_service_v3 import AlertServiceV3
                result = await AlertServiceV3.create_alert(
                    stream_id=sample_stream_id,
                    task_id=sample_task_id,
                    result=sample_alert_result,
                )

            assert result["status"] == "pending"
            assert "alert_id" in result

    @pytest.mark.asyncio
    async def test_create_alert_stores_in_db(self, sample_alert_result, sample_stream_id, sample_task_id):
        with patch("services.alert_service_v3.DatabaseManager") as mock_db:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            added_alerts = []
            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
                added_alerts.append(obj)
            mock_session.add.side_effect = capture_add

            with patch("services.alert_service_v3.asyncio.create_task"):
                from services.alert_service_v3 import AlertServiceV3
                await AlertServiceV3.create_alert(
                    stream_id=sample_stream_id,
                    task_id=sample_task_id,
                    result=sample_alert_result,
                )

            assert len(added_alerts) == 1
            alert = added_alerts[0]
            assert alert.level == "warning"
            assert alert.status == AlertStatusEnum.PENDING
            assert alert.message == "检测到安全帽未佩戴"

    @pytest.mark.asyncio
    async def test_create_alert_triggers_push(self, sample_alert_result, sample_stream_id, sample_task_id):
        with patch("services.alert_service_v3.DatabaseManager") as mock_db:
            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
            mock_session.add.side_effect = capture_add

            with patch("services.alert_service_v3.asyncio.create_task") as mock_create_task:
                from services.alert_service_v3 import AlertServiceV3
                await AlertServiceV3.create_alert(
                    stream_id=sample_stream_id,
                    task_id=sample_task_id,
                    result=sample_alert_result,
                )

            mock_create_task.assert_called_once()


# ALERT-03: State machine transitions
class TestUpdateAlertStatus:
    @pytest.mark.asyncio
    async def test_pending_to_confirmed(self):
        from services.alert_service_v3 import AlertServiceV3
        # Valid: pending -> confirmed
        allowed = AlertServiceV3.VALID_TRANSITIONS[AlertStatusEnum.PENDING]
        assert AlertStatusEnum.CONFIRMED in allowed

    @pytest.mark.asyncio
    async def test_pending_to_dismissed(self):
        from services.alert_service_v3 import AlertServiceV3
        allowed = AlertServiceV3.VALID_TRANSITIONS[AlertStatusEnum.PENDING]
        assert AlertStatusEnum.DISMISSED in allowed

    @pytest.mark.asyncio
    async def test_confirmed_to_resolved(self):
        from services.alert_service_v3 import AlertServiceV3
        allowed = AlertServiceV3.VALID_TRANSITIONS[AlertStatusEnum.CONFIRMED]
        assert AlertStatusEnum.RESOLVED in allowed

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(self):
        from services.alert_service_v3 import AlertServiceV3
        # CONFIRMED -> PENDING is invalid
        allowed = AlertServiceV3.VALID_TRANSITIONS[AlertStatusEnum.CONFIRMED]
        assert AlertStatusEnum.PENDING not in allowed

    @pytest.mark.asyncio
    async def test_resolved_is_terminal(self):
        from services.alert_service_v3 import AlertServiceV3
        allowed = AlertServiceV3.VALID_TRANSITIONS[AlertStatusEnum.RESOLVED]
        assert len(allowed) == 0


# ALERT-04: Feedback data persists to result JSONB
class TestFeedbackStatistics:
    @pytest.mark.asyncio
    async def test_feedback_statistics_counts(self):
        with patch("services.alert_service_v3.DatabaseManager") as mock_db:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = [
                (AlertStatusEnum.PENDING, 5),
                (AlertStatusEnum.CONFIRMED, 3),
                (AlertStatusEnum.DISMISSED, 1),
                (AlertStatusEnum.RESOLVED, 2),
            ]
            mock_session.execute = AsyncMock(return_value=mock_result)
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.alert_service_v3 import AlertServiceV3
            stats = await AlertServiceV3.get_feedback_statistics()

            assert stats["pending"] == 5
            assert stats["confirmed"] == 3
            assert stats["dismissed"] == 1
            assert stats["resolved"] == 2

    @pytest.mark.asyncio
    async def test_feedback_data_in_result_jsonb(self):
        """Verify update_alert_status adds feedback_at/feedback_by/feedback_action to result"""
        with patch("services.alert_service_v3.DatabaseManager") as mock_db, \
             patch("services.alert_service_v3.flag_modified") as mock_flag:
            # Use a simple namespace to avoid SQLAlchemy internals
            class FakeAlert:
                pass
            mock_alert = FakeAlert()
            mock_alert.status = AlertStatusEnum.PENDING
            mock_alert.result = {"has_violation": True}
            mock_alert.id = uuid4()
            mock_alert.created_at = datetime.now(timezone.utc)

            mock_session = AsyncMock()
            mock_scalar = MagicMock()
            mock_scalar.scalar_one_or_none.return_value = mock_alert
            mock_session.execute = AsyncMock(return_value=mock_scalar)
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            from services.alert_service_v3 import AlertServiceV3
            result = await AlertServiceV3.update_alert_status(
                alert_id=str(mock_alert.id),
                created_at=mock_alert.created_at,
                new_status=AlertStatusEnum.CONFIRMED,
                feedback_by="test_user",
            )

            assert result is True
            assert mock_alert.result["feedback_by"] == "test_user"
            assert mock_alert.result["feedback_action"] == "confirmed"
            assert "feedback_at" in mock_alert.result
            mock_flag.assert_called_once_with(mock_alert, "result")
