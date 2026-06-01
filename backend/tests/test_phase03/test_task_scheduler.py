"""SchedulerService tests (SCHED-01, SCHED-03)"""
import pytest


class TestSchedulerService:
    def test_singleton_pattern(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    def test_uses_sqlalchemy_jobstore(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    @pytest.mark.asyncio
    async def test_start_and_shutdown(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    def test_add_and_remove_job(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    def test_remove_jobs_for_stream(self):
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")

    @pytest.mark.asyncio
    async def test_graceful_shutdown_saves_state(self):
        """SCHED-03: shutdown(wait=True) preserves jobs"""
        pytest.skip("MISSING - awaiting SchedulerService implementation (Plan 03-02)")
