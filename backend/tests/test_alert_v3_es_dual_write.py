"""v3 告警 ES 双写测试

覆盖点：
  1. create_alert 成功后调用 elasticsearch_service.index_alert，且 alert_doc 字段完整
  2. index_alert 抛异常 -> create_alert 仍正常返回（PG 主链路不受影响）
  3. update_alert_fields 抛异常 -> update_alert_clip 仍正常 commit PG
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


def _fake_push_module():
    """伪装 services.alert_push_service 模块（当前环境可能缺依赖）"""
    m = MagicMock()
    m.AlertPushService = MagicMock()
    m.AlertPushService.push = AsyncMock()
    return m


# ---------------------------------------------------------------------
# 1. create_alert 成功后调 index_alert 且字段完整
# ---------------------------------------------------------------------
class TestCreateAlertIndexesES:
    @pytest.mark.asyncio
    async def test_create_alert_calls_index_alert_with_full_doc(self):
        from services import alert_service_v3 as mod

        sample_stream = str(uuid4())
        sample_task = str(uuid4())
        sample_result = {
            "has_violation": True,
            "confidence": 0.92,
            "severity": "warning",
            "description": "工人未戴安全帽",
            "violation_type": "no_helmet",
            "image_url": "http://minio/images/a.jpg",
            "detection_objects": [{"bbox": [1, 2, 3, 4], "label": "person"}],
            "image_size": {"w": 1920, "h": 1080},
            "stream_name": "摄像头A",
            "algorithm_name": "安全帽检测",
            "template_name": "安全帽检测",
        }

        fake_es = MagicMock()
        fake_es.index_alert = AsyncMock(return_value=True)
        fake_es_module = MagicMock()
        fake_es_module.elasticsearch_service = fake_es

        with patch.object(mod, "DatabaseManager") as mock_db, \
             patch.object(mod.AlertServiceV3, "_schedule_clip_generation"), \
             patch.dict(sys.modules, {
                 "services.elasticsearch_service": fake_es_module,
                 "services.alert_push_service": _fake_push_module(),
             }), \
             patch.object(mod.asyncio, "create_task"):

            mock_session = AsyncMock()
            mock_session.add = MagicMock()
            mock_session.flush = AsyncMock()
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            captured_id = {"val": None}

            def capture_add(obj):
                obj.id = uuid4()
                obj.created_at = datetime.now(timezone.utc)
                captured_id["val"] = str(obj.id)
            mock_session.add.side_effect = capture_add

            ret = await mod.AlertServiceV3.create_alert(
                stream_id=sample_stream,
                task_id=sample_task,
                result=sample_result,
                snapshot_path="/snap/a.jpg",
            )

            assert ret["status"] == "pending"
            fake_es.index_alert.assert_awaited_once()
            doc = fake_es.index_alert.call_args.args[0]

            # doc id 与 AlertDB.id 一致
            assert doc["id"] == captured_id["val"]
            # 源标记
            assert doc["source"] == "v3"
            # 基础字段
            assert doc["stream_id"] == sample_stream
            assert doc["task_id"] == sample_task
            assert doc["created_at"] is not None
            # 业务字段铺平
            assert doc["violation_type"] == "no_helmet"
            assert doc["confidence"] == 0.92
            assert doc["severity"] == "warning"
            assert doc["description"] == "工人未戴安全帽"
            assert doc["image_url"] == "http://minio/images/a.jpg"
            assert doc["detection_objects"] == [
                {"bbox": [1, 2, 3, 4], "label": "person"}
            ]
            assert doc["image_size"] == {"w": 1920, "h": 1080}
            assert doc["stream_name"] == "摄像头A"
            assert doc["algorithm_name"] == "安全帽检测"
            # clip 初始状态
            assert doc["clip_status"] == "pending"
            # 保留原始 result
            assert doc["result"] == sample_result

    @pytest.mark.asyncio
    async def test_index_alert_failure_does_not_break_create(self):
        """ES 双写抛异常时 create_alert 仍正常返回，PG 主链路不受影响"""
        from services import alert_service_v3 as mod

        sample_stream = str(uuid4())
        sample_task = str(uuid4())
        sample_result = {"description": "x", "severity": "warning"}

        fake_es = MagicMock()
        fake_es.index_alert = AsyncMock(side_effect=RuntimeError("ES 挂了"))
        fake_es_module = MagicMock()
        fake_es_module.elasticsearch_service = fake_es

        with patch.object(mod, "DatabaseManager") as mock_db, \
             patch.object(mod.AlertServiceV3, "_schedule_clip_generation"), \
             patch.dict(sys.modules, {
                 "services.elasticsearch_service": fake_es_module,
                 "services.alert_push_service": _fake_push_module(),
             }), \
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

            ret = await mod.AlertServiceV3.create_alert(
                stream_id=sample_stream,
                task_id=sample_task,
                result=sample_result,
            )
            assert ret["status"] == "pending"
            fake_es.index_alert.assert_awaited_once()


# ---------------------------------------------------------------------
# 2. update_alert_clip: ES 更新失败不影响 PG commit
# ---------------------------------------------------------------------
class TestUpdateAlertClipEsFailureIsolation:
    @pytest.mark.asyncio
    async def test_update_alert_fields_failure_does_not_break_pg(self):
        from services import alert_service_v3 as mod

        alert_id = str(uuid4())

        fake_es = MagicMock()
        fake_es.update_alert_fields = AsyncMock(
            side_effect=RuntimeError("ES 更新挂了")
        )
        fake_es_module = MagicMock()
        fake_es_module.elasticsearch_service = fake_es

        with patch.object(mod, "DatabaseManager") as mock_db, \
             patch.dict(sys.modules, {"services.elasticsearch_service": fake_es_module}):

            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_result = MagicMock()
            mock_result.rowcount = 1
            mock_session.execute.return_value = mock_result
            mock_db.get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=False)

            # 不应抛出 — ES 失败是 best-effort
            ok = await mod.AlertServiceV3.update_alert_clip(
                alert_id=alert_id,
                clip_url="http://minio/clips/x.mp4",
                clip_status="ready",
            )
            assert ok is True
            # PG 被执行
            mock_session.execute.assert_awaited()
            # ES 被调用但失败
            fake_es.update_alert_fields.assert_awaited_once()
