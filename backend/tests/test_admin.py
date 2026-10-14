"""Admin shell tests (slice-07): authorization, audit-log sink + read endpoint."""
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.audit_log import AuditLog
from app.models.user import User
from app.services import audit_log_service
from app.services.jwt_service import issue_token
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str, role: str):
    token = issue_token(user_id, role, f"{user_id}@test.com")
    return {"Authorization": f"Bearer {token}"}


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def seed_user(user_id: str, full_name: str, role: str = "end_user"):
    async with TestingSessionLocal() as s:
        s.add(
            User(
                user_id=user_id,
                email=f"{user_id}@test.com",
                full_name=full_name,
                role=role,
                external_id=f"ext-{user_id}",
            )
        )
        await s.commit()


async def seed_log(role_pack, action_type, *, actor_id=None, reference_id=None, details=None, created_at=None):
    async with TestingSessionLocal() as s:
        entry = AuditLog(
            user_id=actor_id,
            role_pack=role_pack,
            action_type=action_type,
            reference_id=reference_id,
            details=details,
        )
        if created_at:
            entry.created_at = created_at
        s.add(entry)
        await s.commit()


# --- Authorization ----------------------------------------------------------


@pytest.mark.asyncio
async def test_non_admin_gets_403():
    """AC: a non-admin JWT on any /api/admin/* route returns 403."""
    async with _client() as client:
        res = await client.get("/api/admin/audit-log", headers=headers_for("u1", "end_user"))
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_missing_token_gets_401():
    """No token is rejected upstream by the gateway middleware (401, not 403)."""
    async with _client() as client:
        res = await client.get("/api/admin/audit-log")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_each_admin_role_maps_to_its_pack():
    """AC: an admin only ever sees their own role pack's entries."""
    await seed_log("hr", "leave_submitted")
    await seed_log("it", "ticket_created")
    await seed_log("admissions", "app_submitted")

    async with _client() as client:
        hr = await client.get("/api/admin/audit-log", headers=headers_for("a1", "hr_admin"))
        it = await client.get("/api/admin/audit-log", headers=headers_for("a2", "it_admin"))
        adm = await client.get("/api/admin/audit-log", headers=headers_for("a3", "admissions_admin"))

    for res, pack, action in [
        (hr, "hr", "leave_submitted"),
        (it, "it", "ticket_created"),
        (adm, "admissions", "app_submitted"),
    ]:
        data = res.json()["data"]
        assert res.status_code == 200
        assert data["role_pack"] == pack
        assert data["total"] == 1
        assert {e["action_type"] for e in data["entries"]} == {action}


@pytest.mark.asyncio
async def test_hr_admin_never_sees_other_packs():
    """AC: an hr_admin cannot read IT/Admissions data (scoped away)."""
    await seed_log("it", "ticket_created")
    await seed_log("admissions", "app_submitted")

    async with _client() as client:
        res = await client.get("/api/admin/audit-log", headers=headers_for("a1", "hr_admin"))

    data = res.json()["data"]
    assert data["role_pack"] == "hr"
    assert data["total"] == 0
    assert data["entries"] == []


# --- audit-log sink ---------------------------------------------------------


@pytest.mark.asyncio
async def test_sink_appends_row():
    """AC: calling the sink appends an audit_log row with all fields."""
    async with TestingSessionLocal() as s:
        entry = await audit_log_service.record(
            s,
            actor_id="u1",
            role_pack="hr",
            action_type="leave_submitted",
            reference_id="LEAVE-2031",
            details={"leave_type": "casual", "days": 2},
        )
    assert entry is not None

    async with _client() as client:
        res = await client.get("/api/admin/audit-log", headers=headers_for("a1", "hr_admin"))

    row = res.json()["data"]["entries"][0]
    assert row["action_type"] == "leave_submitted"
    assert row["actor_id"] == "u1"
    assert row["reference_id"] == "LEAVE-2031"
    assert row["details"] == {"leave_type": "casual", "days": 2}


@pytest.mark.asyncio
async def test_read_resolves_actor_name():
    """The endpoint joins the actor's name for display."""
    await seed_user("u1", "John Doe")
    await seed_log("hr", "leave_submitted", actor_id="u1", reference_id="LEAVE-1")

    async with _client() as client:
        res = await client.get("/api/admin/audit-log", headers=headers_for("a1", "hr_admin"))

    assert res.json()["data"]["entries"][0]["actor_name"] == "John Doe"


# --- filters + pagination ---------------------------------------------------


@pytest.mark.asyncio
async def test_filters_and_pagination():
    """AC: audit-log honours action_type / actor_id / from-to / limit-offset."""
    base = datetime(2026, 9, 1, 10, 0, 0)
    for i in range(5):
        await seed_log(
            "hr",
            "leave_submitted" if i % 2 == 0 else "intent_updated",
            actor_id="u1" if i < 3 else "u2",
            created_at=base + timedelta(days=i),
        )

    async with _client() as client:
        hdr = headers_for("a1", "hr_admin")

        # action_type filter
        by_action = await client.get("/api/admin/audit-log?action_type=leave_submitted", headers=hdr)
        assert by_action.json()["data"]["total"] == 3

        # actor_id filter
        by_actor = await client.get("/api/admin/audit-log?actor_id=u2", headers=hdr)
        assert by_actor.json()["data"]["total"] == 2

        # date range filter (days 1..2 inclusive)
        rng = await client.get(
            "/api/admin/audit-log?from=2026-09-02T00:00:00&to=2026-09-03T23:59:59", headers=hdr
        )
        assert rng.json()["data"]["total"] == 2

        # pagination: total unchanged, page size respected
        page = await client.get("/api/admin/audit-log?limit=2&offset=0", headers=hdr)
        body = page.json()["data"]
        assert body["total"] == 5
        assert len(body["entries"]) == 2


@pytest.mark.asyncio
async def test_malformed_date_is_422():
    async with _client() as client:
        res = await client.get("/api/admin/audit-log?from=not-a-date", headers=headers_for("a1", "hr_admin"))
    assert res.status_code == 422
