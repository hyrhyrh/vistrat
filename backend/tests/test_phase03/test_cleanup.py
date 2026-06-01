"""Cascade cleanup and MinIO scheduled cleanup tests (SCHED-04, INFRA-02)"""
import pytest


class TestStreamDeleteCascade:
    @pytest.mark.asyncio
    async def test_delete_stops_analysis_tasks(self):
        """SCHED-04: delete stream stops associated pipeline tasks"""
        pytest.skip("MISSING - awaiting StreamService cascade cleanup (Plan 03-03)")

    @pytest.mark.asyncio
    async def test_delete_removes_scheduler_jobs(self):
        """SCHED-04: delete stream removes APScheduler jobs"""
        pytest.skip("MISSING - awaiting StreamService cascade cleanup (Plan 03-03)")

    @pytest.mark.asyncio
    async def test_delete_cleans_minio_frames(self):
        """SCHED-04: delete stream cleans MinIO frame screenshots"""
        pytest.skip("MISSING - awaiting StreamService cascade cleanup (Plan 03-03)")


class TestMinIOCleanupService:
    @pytest.mark.asyncio
    async def test_cleanup_expired_frames(self):
        """INFRA-02: scheduled cleanup of expired frames"""
        pytest.skip("MISSING - awaiting MinIOCleanupService implementation (Plan 03-03)")

    def test_register_cleanup_job(self):
        """INFRA-02: APScheduler interval trigger registration"""
        pytest.skip("MISSING - awaiting MinIOCleanupService implementation (Plan 03-03)")
