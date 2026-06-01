"""
告警服务单元测试
覆盖 WebSocket 连接管理、告警广播、严重程度判定、历史记录、频次控制等场景
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from core.alert_service import AlertService


# ============================================================================
# 测试前后清理
# ============================================================================

@pytest.fixture(autouse=True)
def _reset_alert_service():
    """每个测试前重置 AlertService 类状态"""
    AlertService._connections.clear()
    AlertService._alert_history.clear()
    AlertService._alert_throttle_cache.clear()
    yield
    AlertService._connections.clear()
    AlertService._alert_history.clear()
    AlertService._alert_throttle_cache.clear()


# ============================================================================
# WebSocket 连接管理测试
# ============================================================================

class TestWebSocketRegistration:
    """WebSocket 连接注册/注销测试"""

    @pytest.mark.asyncio
    async def test_register_无认证要求正常注册(self, mock_websocket):
        """WS_AUTH_REQUIRED=false 时应直接接受连接"""
        with patch("core.alert_service.WS_AUTH_REQUIRED", False):
            result = await AlertService.register(mock_websocket)
            assert result is True
            mock_websocket.accept.assert_called_once()
            assert mock_websocket in AlertService._connections

    @pytest.mark.asyncio
    async def test_register_需要认证但无token时拒绝(self, mock_websocket):
        """WS_AUTH_REQUIRED=true 且无 token 应拒绝连接"""
        with patch("core.alert_service.WS_AUTH_REQUIRED", True):
            result = await AlertService.register(mock_websocket, token=None)
            assert result is False
            mock_websocket.close.assert_called_once()
            assert mock_websocket not in AlertService._connections

    @pytest.mark.asyncio
    async def test_register_需要认证且token有效时接受(self, mock_websocket):
        """WS_AUTH_REQUIRED=true 且 token 有效应接受"""
        mock_token_data = MagicMock()
        mock_token_data.username = "testuser"

        with patch("core.alert_service.WS_AUTH_REQUIRED", True), \
             patch("services.auth_service.AuthService._verify_token",
                   return_value=mock_token_data):
            result = await AlertService.register(mock_websocket, token="valid-token")
            assert result is True
            assert mock_websocket in AlertService._connections

    @pytest.mark.asyncio
    async def test_register_需要认证且token无效时拒绝(self, mock_websocket):
        """WS_AUTH_REQUIRED=true 且 token 无效应拒绝"""
        with patch("core.alert_service.WS_AUTH_REQUIRED", True), \
             patch("services.auth_service.AuthService._verify_token",
                   return_value=None):
            result = await AlertService.register(mock_websocket, token="invalid-token")
            assert result is False
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_移除连接(self, mock_websocket):
        """注销应从连接集合中移除 WebSocket"""
        AlertService._connections.add(mock_websocket)
        assert mock_websocket in AlertService._connections

        await AlertService.unregister(mock_websocket)
        assert mock_websocket not in AlertService._connections

    @pytest.mark.asyncio
    async def test_unregister_不存在的连接不报错(self, mock_websocket):
        """注销不存在的连接不应抛出异常"""
        await AlertService.unregister(mock_websocket)  # 不应报错


# ============================================================================
# 告警广播测试
# ============================================================================

class TestNotify:
    """告警广播（notify）测试"""

    @pytest.mark.asyncio
    async def test_notify_发送给所有连接(self):
        """告警应发送给所有已连接的客户端"""
        ws1, ws2 = AsyncMock(), AsyncMock()
        AlertService._connections = {ws1, ws2}

        await AlertService.notify({"alert": "测试告警", "description": "测试"})

        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_断开的连接被清理(self):
        """发送失败的连接应被自动清理"""
        ws_good = AsyncMock()
        ws_bad = AsyncMock()
        ws_bad.send_text.side_effect = Exception("connection closed")
        AlertService._connections = {ws_good, ws_bad}

        await AlertService.notify({"alert": "测试", "description": ""})

        assert ws_bad not in AlertService._connections
        assert ws_good in AlertService._connections

    @pytest.mark.asyncio
    async def test_notify_添加到历史记录(self):
        """告警应被添加到历史记录"""
        await AlertService.notify({"alert": "新告警", "description": "测试描述"})

        assert len(AlertService._alert_history) == 1
        assert AlertService._alert_history[0].alert == "新告警"

    @pytest.mark.asyncio
    async def test_notify_历史记录最多1000条(self):
        """历史记录应限制在 1000 条"""
        # 预填充 1000 条
        from models.alert import AlertMessage
        AlertService._alert_history = [
            AlertMessage(alert=f"告警{i}", severity="low") for i in range(1000)
        ]

        await AlertService.notify({"alert": "新告警", "description": ""})

        assert len(AlertService._alert_history) == 1000
        assert AlertService._alert_history[0].alert == "新告警"

    @pytest.mark.asyncio
    async def test_notify_无连接时不报错(self):
        """无连接时应正常执行不报错"""
        AlertService._connections.clear()
        await AlertService.notify({"alert": "无人收听", "description": ""})
        assert len(AlertService._alert_history) == 1


# ============================================================================
# 严重程度判定测试
# ============================================================================

class TestDetermineSeverity:
    """告警严重程度判定测试"""

    @pytest.mark.parametrize("alert_text,expected", [
        ("检测到危险行为", "high"),
        ("火灾报警", "high"),
        ("暴力行为", "high"),
        ("发现异常情况", "medium"),
        ("可疑人员", "medium"),
        ("违规操作", "medium"),
        ("正常巡逻", "low"),
        ("无异常", "low"),
        ("", "low"),
    ])
    def test_determine_severity_各场景(self, alert_text, expected):
        """各种告警文本应返回正确的严重程度"""
        assert AlertService._determine_severity(alert_text) == expected

    def test_determine_severity_None输入返回low(self):
        """None 输入应返回 low"""
        assert AlertService._determine_severity(None) == "low"


# ============================================================================
# 历史记录测试
# ============================================================================

class TestGetHistory:
    """告警历史记录查询测试"""

    def test_get_history_空历史(self):
        """空历史应返回空列表"""
        result = AlertService.get_history()
        assert result["data"] == []
        assert result["total"] == 0

    def test_get_history_分页(self):
        """应支持分页查询"""
        from models.alert import AlertMessage
        AlertService._alert_history = [
            AlertMessage(alert=f"告警{i}", severity="low") for i in range(25)
        ]

        result = AlertService.get_history(limit=10, offset=0)
        assert len(result["data"]) == 10
        assert result["total"] == 25
        assert result["page"] == 1
        assert result["page_size"] == 10

    def test_get_history_第二页(self):
        """应正确返回第二页数据"""
        from models.alert import AlertMessage
        AlertService._alert_history = [
            AlertMessage(alert=f"告警{i}", severity="low") for i in range(25)
        ]

        result = AlertService.get_history(limit=10, offset=10)
        assert len(result["data"]) == 10
        assert result["page"] == 2

    def test_clear_history_清空(self):
        """clear_history 应清空所有记录"""
        from models.alert import AlertMessage
        AlertService._alert_history = [
            AlertMessage(alert="test", severity="low")
        ]
        AlertService.clear_history()
        assert len(AlertService._alert_history) == 0


# ============================================================================
# 时间格式化测试
# ============================================================================

class TestFormatVideoTime:
    """视频时间格式化测试"""

    @pytest.mark.parametrize("seconds,expected", [
        (0.0, "00:00"),
        (65.0, "01:05"),
        (3600.0, "60:00"),
        (125.5, "02:05"),
    ])
    def test_format_video_time_各种秒数(self, seconds, expected):
        """各种秒数应正确转换为 MM:SS 格式"""
        assert AlertService._format_video_time(seconds) == expected

    def test_format_video_time_异常输入返回默认(self):
        """异常输入应返回 00:00"""
        assert AlertService._format_video_time("not_a_number") == "00:00"


# ============================================================================
# 告警频次控制测试
# ============================================================================

class TestAlertThrottling:
    """告警频次控制测试"""

    @pytest.mark.asyncio
    async def test_broadcast_alert_首次发送通过(self):
        """首次发送告警应通过频次检查"""
        alert_msg = {
            "id": "a1",
            "message": "测试告警",
            "description": "测试",
            "source": "camera1",
            "task_id": "t1",
            "frame_index": 0,
        }

        mock_es_module = MagicMock()
        mock_es_module.elasticsearch_service = AsyncMock()
        mock_es_module.elasticsearch_service.store_alert = AsyncMock()

        with patch.object(AlertService, "notify", new_callable=AsyncMock) as mock_notify, \
             patch.dict("sys.modules", {"services.elasticsearch_service": mock_es_module}):
            await AlertService.broadcast_alert(alert_msg)
            mock_notify.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_alert_重复告警被限流(self):
        """短时间内相同告警应被限流"""
        from utils.timezone_utils import now

        alert_key = "测试告警_camera1"
        AlertService._alert_throttle_cache[alert_key] = now()

        alert_msg = {
            "id": "a2",
            "message": "测试告警",
            "source": "camera1",
        }

        with patch.object(AlertService, "notify", new_callable=AsyncMock) as mock_notify:
            await AlertService.broadcast_alert(alert_msg)
            # 被限流，不应调用 notify
            mock_notify.assert_not_called()

    @pytest.mark.asyncio
    async def test_broadcast_alert_超过间隔后允许发送(self):
        """超过限流间隔后应允许再次发送"""
        from utils.timezone_utils import now

        alert_key = "过期告警_camera2"
        # 设置为 4 小时前（超过默认 3 小时间隔）
        AlertService._alert_throttle_cache[alert_key] = now() - timedelta(hours=4)

        alert_msg = {
            "id": "a3",
            "message": "过期告警",
            "source": "camera2",
            "task_id": "t2",
            "frame_index": 1,
        }

        mock_es_module = MagicMock()
        mock_es_module.elasticsearch_service = AsyncMock()
        mock_es_module.elasticsearch_service.store_alert = AsyncMock()

        with patch.object(AlertService, "notify", new_callable=AsyncMock) as mock_notify, \
             patch.dict("sys.modules", {"services.elasticsearch_service": mock_es_module}):
            await AlertService.broadcast_alert(alert_msg)
            mock_notify.assert_called_once()
