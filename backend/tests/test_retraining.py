"""Slice 10 tests for durable retraining job state and role-pack access."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.jwt_service import issue_token


def auth(user_id: str, role: str):
    return {"Authorization": f"Bearer {issue_token(user_id, role, f'{user_id}@test.com')}"}


HR = auth("retrain-hr", "hr_admin")
IT = auth("retrain-it", "it_admin")
USER = auth("retrain-user", "end_user")


@pytest.mark.asyncio
async def test_retraining_job_is_persisted_and_role_scoped(monkeypatch):
    # Keep the background worker dormant so this test exercises durable job creation
    # and retrieval without calling a live role-pack runtime.
    import asyncio
    from app.services import retraining_service
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr(asyncio, "create_task", lambda coroutine: coroutine.close())
    monkeypatch.setattr(retraining_service, "AsyncSessionLocal", TestingSessionLocal)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/admin/retrain", headers=HR)
        assert created.status_code == 202
        job_id = created.json()["data"]["retrain_job_id"]

        own_job = await client.get(f"/api/admin/retrain/{job_id}", headers=HR)
        assert own_job.status_code == 200
        assert own_job.json()["data"]["job_id"] == job_id
        assert own_job.json()["data"]["role_pack"] == "hr"
        assert own_job.json()["data"]["state"] == "pending"
        assert "actor_id" not in own_job.json()["data"]

        other_pack = await client.get(f"/api/admin/retrain/{job_id}", headers=IT)
        assert other_pack.status_code == 404

        non_admin = await client.post("/api/admin/retrain", headers=USER)
        assert non_admin.status_code == 403


@pytest.mark.asyncio
async def test_retraining_job_not_found_returns_404(monkeypatch):
    from app.services import retraining_service
    from tests.conftest import TestingSessionLocal

    monkeypatch.setattr(retraining_service, "AsyncSessionLocal", TestingSessionLocal)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/admin/retrain/00000000-0000-0000-0000-000000000000", headers=HR
        )
    assert response.status_code == 404
