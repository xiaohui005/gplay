import pytest
from src.services.task_scheduler import TaskScheduler


class TestTaskScheduler:
    def test_scheduler_start_and_stop(self):
        scheduler = TaskScheduler()
        assert scheduler._started is False

        scheduler.start()
        assert scheduler._started is True
        assert scheduler.scheduler.running is True

        scheduler.stop()
        assert scheduler._started is False

    def test_scheduler_idempotent_start(self):
        scheduler = TaskScheduler()
        scheduler.start()
        scheduler.start()
        assert scheduler._started is True
        scheduler.stop()

    def test_registered_jobs(self):
        scheduler = TaskScheduler()
        scheduler._register_jobs()
        job_ids = [job.id for job in scheduler.scheduler.get_jobs()]
        assert "collect_stock_basic_daily" in job_ids
        assert "collect_quote_5min" in job_ids
        assert "collect_kline_daily" in job_ids
        assert "retry_failed_jobs_15min" in job_ids
        assert len(job_ids) >= 10
