"""Phase 3 test fixtures"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def mock_db_session():
    """Mock async DB session"""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def sample_alert_result():
    """Sample AI analysis result with violation"""
    return {
        "has_violation": True,
        "confidence": 0.85,
        "severity": "warning",
        "description": "检测到安全帽未佩戴",
        "violation_type": "no_helmet",
    }


@pytest.fixture
def sample_stream_id():
    return str(uuid4())


@pytest.fixture
def sample_task_id():
    return str(uuid4())


@pytest.fixture
def mock_minio_client():
    """Mock MinIO client"""
    client = AsyncMock()
    client.cleanup_expired_files = AsyncMock(return_value=5)
    client.delete_file = AsyncMock(return_value=True)
    return client
