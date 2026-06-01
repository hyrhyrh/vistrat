"""
共享测试 fixtures
提供常用的 mock 对象和测试数据
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# 确保 backend 目录在 sys.path 中
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))


# ---------------------------------------------------------------------------
# 基础数据 fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_user_id():
    """示例用户 UUID"""
    return str(uuid4())


@pytest.fixture
def sample_user_data():
    """示例用户数据（用于创建用户）"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "测试用户",
        "role": "user",
    }


@pytest.fixture
def sample_admin_data():
    """示例管理员数据"""
    return {
        "username": "admin",
        "email": "admin@example.com",
        "password": "admin123",
        "full_name": "系统管理员",
        "role": "admin",
    }


@pytest.fixture
def sample_video_data():
    """示例视频文件元数据"""
    return {
        "id": str(uuid4()),
        "filename": "test_video.mp4",
        "file_path": "/uploads/test_video.mp4",
        "file_size": 1024 * 1024 * 50,  # 50MB
        "duration": 120.0,
        "fps": 25.0,
        "width": 1920,
        "height": 1080,
        "status": "uploaded",
    }


@pytest.fixture
def sample_alert_data():
    """示例告警数据"""
    return {
        "alert": "检测到可疑行为",
        "description": "摄像头区域内检测到异常人员活动",
        "video_file_name": "warning_001.mp4",
        "picture_file_name": "warning_001.jpg",
        "severity": "medium",
    }


@pytest.fixture
def sample_analysis_result():
    """示例分析结果"""
    return {
        "alert": "火灾隐患",
        "description": "检测到浓烟，可能存在火灾隐患",
        "video_file_name": "fire_alert.mp4",
        "picture_file_name": "fire_alert.jpg",
        "confidence": 0.92,
        "analysis_time": 2.5,
    }


# ---------------------------------------------------------------------------
# Mock fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_db_session():
    """模拟数据库 session（异步上下文管理器）"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_redis():
    """模拟 Redis 客户端"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.expire = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_es_client():
    """模拟 Elasticsearch 客户端"""
    es = AsyncMock()
    es.index = AsyncMock(return_value={"result": "created"})
    es.search = AsyncMock(return_value={"hits": {"hits": [], "total": {"value": 0}}})
    es.delete = AsyncMock(return_value={"result": "deleted"})
    return es


@pytest.fixture
def mock_minio_client():
    """模拟 MinIO 客户端"""
    client = AsyncMock()
    client.upload_file = AsyncMock(return_value={"key": "test/object.jpg", "size": 1024})
    client.get_presigned_url = AsyncMock(return_value="http://minio:9000/bucket/test.jpg")
    client.delete_file = AsyncMock(return_value=True)
    return client


@pytest.fixture
def mock_websocket():
    """模拟 WebSocket 连接"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    ws.receive_text = AsyncMock(return_value='{"type": "ping"}')
    return ws
