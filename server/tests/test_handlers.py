import os
import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite:///./data/test_handlers.db"

from src.main import app
from src.collectors.registry import CollectorRegistry
from src.collectors.mock_collector import MockCollector


@pytest.fixture(autouse=True, scope="module")
def setup():
    CollectorRegistry.register(MockCollector)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestAdminHandlers:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_manual_trigger_success(self, client):
        resp = client.post(
            "/api/admin/data-collection/jobs",
            json={
                "dataType": "MOCK",
                "symbols": ["600000", "000001"],
                "reason": "test",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["successCount"] == 2
        assert data["triggerType"] == "MANUAL"
        assert data["taskId"].startswith("job_")

    def test_manual_trigger_invalid_type(self, client):
        resp = client.post(
            "/api/admin/data-collection/jobs",
            json={
                "dataType": "INVALID_TYPE",
                "reason": "test",
            },
        )
        assert resp.status_code == 400

    def test_list_jobs(self, client):
        resp = client.get("/api/admin/data-collection/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    def test_list_jobs_filtered(self, client):
        resp = client.get(
            "/api/admin/data-collection/jobs",
            params={"dataType": "MOCK", "pageSize": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["dataType"] == "MOCK"

    def test_get_job(self, client):
        create_resp = client.post(
            "/api/admin/data-collection/jobs",
            json={"dataType": "MOCK", "symbols": ["600000"], "reason": "test"},
        )
        task_id = create_resp.json()["taskId"]

        resp = client.get(f"/api/admin/data-collection/jobs/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["taskId"] == task_id

    def test_get_job_not_found(self, client):
        resp = client.get("/api/admin/data-collection/jobs/nonexistent")
        assert resp.status_code == 404

    def test_retry_job(self, client):
        create_resp = client.post(
            "/api/admin/data-collection/jobs",
            json={"dataType": "MOCK", "symbols": ["FAIL_SYMBOL"], "reason": "test"},
        )
        task_id = create_resp.json()["taskId"]

        resp = client.post(f"/api/admin/data-collection/jobs/{task_id}/retry")
        if resp.status_code == 400:
            assert "不可重试" in resp.json()["detail"]
        else:
            assert resp.status_code == 200

    def test_list_errors(self, client):
        resp = client.get("/api/admin/data-collection/errors")
        assert resp.status_code == 200
        assert "items" in resp.json()
