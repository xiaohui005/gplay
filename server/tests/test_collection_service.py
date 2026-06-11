import json
import pytest

from src.models.data_collection_job import DataCollectionJob
from src.models.data_collection_error import DataCollectionError
from src.models.raw_market_data import RawMarketData
from src.repositories.data_collection_job_repo import DataCollectionJobRepo
from src.repositories.data_collection_error_repo import DataCollectionErrorRepo
from src.repositories.raw_market_data_repo import RawMarketDataRepo
from src.collectors.registry import CollectorRegistry
from src.collectors.mock_collector import MockCollector
from src.services.collection_service import CollectionService


class TestCollectionService:
    @pytest.fixture(autouse=True)
    def setup(self):
        CollectorRegistry.register(MockCollector)

    def test_create_and_run_success(self, db_session):
        service = CollectionService()
        job = service.create_and_run(
            data_type="MOCK",
            symbols=["600000", "000001"],
            trigger_type="MANUAL",
        )

        assert job.status == "SUCCESS"
        assert job.success_count == 2
        assert job.fail_count == 0
        assert job.trigger_type == "MANUAL"
        assert job.task_id.startswith("job_")
        assert job.batch_id.startswith("batch_")

        raw_repo = RawMarketDataRepo(db_session)
        raws = raw_repo.list_by_batch(job.batch_id)
        assert len(raws) == 2
        for raw in raws:
            payload = json.loads(raw.payload)
            assert "symbol" in payload
            assert "latestPrice" in payload

        error_repo = DataCollectionErrorRepo(db_session)
        errors = error_repo.list_by_batch(job.batch_id)
        assert len(errors) == 0

    def test_create_and_run_partial_failure(self, db_session):
        service = CollectionService()
        job = service.create_and_run(
            data_type="MOCK",
            symbols=["600000", "FAIL_SYMBOL", "000001"],
            trigger_type="MANUAL",
        )

        assert job.status in ("PARTIAL_SUCCESS", "FAILED")
        assert job.success_count == 2
        assert job.fail_count == 1

        raw_repo = RawMarketDataRepo(db_session)
        raws = raw_repo.list_by_batch(job.batch_id)
        assert len(raws) == 2

        error_repo = DataCollectionErrorRepo(db_session)
        errors = error_repo.list_by_batch(job.batch_id)
        if job.fail_count > 0:
            assert len(errors) >= 1
            assert errors[0].symbol == "FAIL_SYMBOL"

    def test_batch_id_generation(self):
        batch_id = CollectionService._generate_batch_id()
        assert batch_id.startswith("batch_")
        assert len(batch_id) > 10

    def test_task_id_generation(self):
        task_id = CollectionService._generate_task_id()
        assert task_id.startswith("job_")
        assert len(task_id) > 10

    def test_job_state_machine(self, db_session):
        service = CollectionService()
        job = service.create_and_run(
            data_type="MOCK",
            symbols=["600000"],
            trigger_type="SCHEDULED",
        )

        assert job.status == "SUCCESS"
        assert job.start_time is not None
        assert job.end_time is not None
        assert job.start_time < job.end_time
