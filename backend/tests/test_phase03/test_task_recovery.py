"""Task recovery tests (SCHED-02)"""
import pytest


class TestTaskRecovery:
    @pytest.mark.asyncio
    async def test_recover_running_tasks(self):
        """SCHED-02: recover all status=running tasks on startup"""
        pytest.skip("MISSING - awaiting SchedulerService.recover_analysis_tasks (Plan 03-02)")

    @pytest.mark.asyncio
    async def test_recovery_skips_failed_tasks(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    @pytest.mark.asyncio
    async def test_recovery_logs_count(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")
