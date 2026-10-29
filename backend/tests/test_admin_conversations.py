import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
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


async def seed_conversation_with_messages(
    conversation_id: str,
    user_id: str,
    role_pack: str,
    title: str,
    messages_data: list,
    created_at: datetime = None,
    last_message_at: datetime = None,
):
    async with TestingSessionLocal() as s:
        now = datetime.utcnow()
        conv = Conversation(
            conversation_id=conversation_id,
            user_id=user_id,
            role_pack=role_pack,
            title=title,
            created_at=created_at or now,
            last_message_at=last_message_at or now,
        )
        s.add(conv)
        await s.flush()

        for idx, m in enumerate(messages_data):
            msg = Message(
                message_id=f"msg-{conversation_id}-{idx}",
                conversation_id=conversation_id,
                sender=m.get("sender", "user"),
                content=m.get("content", ""),
                intent_name=m.get("intent_name"),
                confidence=m.get("confidence"),
                entities=m.get("entities"),
                created_at=m.get("created_at", (created_at or now) + timedelta(seconds=idx)),
            )
            s.add(msg)

        await s.commit()


# --- AC-4: Non-admin authorization check ---


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_conversation_endpoints():
    """Non-admin caller receives 403 on both admin conversation endpoints."""
    await seed_user("end_user_1", "Regular User", "end_user")

    async with _client() as client:
        # List endpoint
        res1 = await client.get("/api/admin/conversations", headers=headers_for("end_user_1", "end_user"))
        assert res1.status_code == 403

        # Transcript endpoint
        res2 = await client.get("/api/admin/conversations/conv-1/messages", headers=headers_for("end_user_1", "end_user"))
        assert res2.status_code == 403


# --- AC-1: List conversations & role-pack scoping & filters & pagination ---


@pytest.mark.asyncio
async def test_admin_conversations_list_role_pack_scoping():
    """Admin GET /api/admin/conversations returns only their role pack's conversations."""
    await seed_user("applicant_aarav", "Aarav Sharma")
    await seed_user("employee_john", "John Doe")
    await seed_user("adm_admin_user", "Admissions Admin", "admissions_admin")
    await seed_user("hr_admin_user", "HR Admin", "hr_admin")

    # Seed 2 admissions conversations
    await seed_conversation_with_messages(
        "conv-adm-1",
        "applicant_aarav",
        "admissions",
        "Fee inquiry",
        [
            {"sender": "user", "content": "How much is B.Tech tuition?"},
            {"sender": "bot", "content": "According to the calendar: ₹3,20,000", "intent_name": "ask_fee_deadline", "confidence": 0.95},
        ],
    )
    await seed_conversation_with_messages(
        "conv-adm-2",
        "applicant_aarav",
        "admissions",
        "Checklist inquiry",
        [
            {"sender": "user", "content": "Documents for MBA?"},
            {"sender": "bot", "content": "Required documents: SOP, Degree", "intent_name": "get_document_checklist", "confidence": 0.92},
        ],
    )

    # Seed 1 HR conversation
    await seed_conversation_with_messages(
        "conv-hr-1",
        "employee_john",
        "hr",
        "Leave balance",
        [
            {"sender": "user", "content": "What is my leave balance?"},
            {"sender": "bot", "content": "You have 12 days left.", "intent_name": "check_leave_balance", "confidence": 0.96},
        ],
    )

    async with _client() as client:
        # Admissions admin sees only admissions conversations
        res_adm = await client.get("/api/admin/conversations", headers=headers_for("adm_admin_user", "admissions_admin"))
        assert res_adm.status_code == 200
        data_adm = res_adm.json()["data"]
        assert data_adm["role_pack"] == "admissions"
        conv_ids = [c["id"] for c in data_adm["conversations"]]
        assert "conv-adm-1" in conv_ids
        assert "conv-adm-2" in conv_ids
        assert "conv-hr-1" not in conv_ids

        # Check conversation fields
        c1 = next(c for c in data_adm["conversations"] if c["id"] == "conv-adm-1")
        assert c1["user_name"] == "Aarav Sharma"
        assert c1["user_email"] == "applicant_aarav@test.com"
        assert c1["title"] == "Fee inquiry"
        assert c1["message_count"] == 2
        assert c1["last_intent"] == "ask_fee_deadline"
        assert "started_at" in c1
        assert "last_message_at" in c1

        # HR admin sees only HR conversations
        res_hr = await client.get("/api/admin/conversations", headers=headers_for("hr_admin_user", "hr_admin"))
        assert res_hr.status_code == 200
        data_hr = res_hr.json()["data"]
        assert data_hr["role_pack"] == "hr"
        hr_conv_ids = [c["id"] for c in data_hr["conversations"]]
        assert "conv-hr-1" in hr_conv_ids
        assert "conv-adm-1" not in hr_conv_ids


@pytest.mark.asyncio
async def test_admin_conversations_list_filters_and_pagination():
    """Filters by actor_id, date range (from/to), and pagination."""
    await seed_user("applicant_diya", "Diya Patel")
    await seed_user("applicant_rohan", "Rohan Gupta")
    await seed_user("adm_admin_user2", "Admissions Admin 2", "admissions_admin")

    t0 = datetime(2026, 9, 1, 10, 0, 0)
    t1 = datetime(2026, 9, 5, 10, 0, 0)
    t2 = datetime(2026, 9, 10, 10, 0, 0)

    await seed_conversation_with_messages(
        "conv-filter-1",
        "applicant_diya",
        "admissions",
        "Application Diya",
        [{"sender": "user", "content": "Status of APP-1002"}],
        created_at=t0,
        last_message_at=t0,
    )
    await seed_conversation_with_messages(
        "conv-filter-2",
        "applicant_rohan",
        "admissions",
        "Application Rohan 1",
        [{"sender": "user", "content": "Status of APP-1003"}],
        created_at=t1,
        last_message_at=t1,
    )
    await seed_conversation_with_messages(
        "conv-filter-3",
        "applicant_rohan",
        "admissions",
        "Application Rohan 2",
        [{"sender": "user", "content": "Fee deadline?"}],
        created_at=t2,
        last_message_at=t2,
    )

    async with _client() as client:
        # Filter by actor_id
        res_actor = await client.get(
            "/api/admin/conversations?actor_id=applicant_diya",
            headers=headers_for("adm_admin_user2", "admissions_admin"),
        )
        assert res_actor.status_code == 200
        actor_data = res_actor.json()["data"]
        assert all(c["user_name"] == "Diya Patel" for c in actor_data["conversations"])
        assert any(c["id"] == "conv-filter-1" for c in actor_data["conversations"])

        # Filter by date range (from Sept 4 to Sept 8)
        res_date = await client.get(
            "/api/admin/conversations?from=2026-09-04T00:00:00Z&to=2026-09-08T00:00:00Z",
            headers=headers_for("adm_admin_user2", "admissions_admin"),
        )
        assert res_date.status_code == 200
        date_data = res_date.json()["data"]
        date_ids = [c["id"] for c in date_data["conversations"]]
        assert "conv-filter-2" in date_ids
        assert "conv-filter-1" not in date_ids
        assert "conv-filter-3" not in date_ids

        # Pagination (limit=1, offset=0 and offset=1)
        res_p1 = await client.get(
            "/api/admin/conversations?limit=1&offset=0",
            headers=headers_for("adm_admin_user2", "admissions_admin"),
        )
        assert res_p1.status_code == 200
        assert len(res_p1.json()["data"]["conversations"]) == 1
        assert res_p1.json()["data"]["total"] >= 3

        res_p2 = await client.get(
            "/api/admin/conversations?limit=1&offset=1",
            headers=headers_for("adm_admin_user2", "admissions_admin"),
        )
        assert res_p2.status_code == 200
        assert len(res_p2.json()["data"]["conversations"]) == 1
        assert res_p1.json()["data"]["conversations"][0]["id"] != res_p2.json()["data"]["conversations"][0]["id"]


# --- AC-2: Transcript with intent + confidence ---


@pytest.mark.asyncio
async def test_admin_transcript_returns_intent_and_confidence():
    """GET /api/admin/conversations/:id/messages returns transcript with bot intent+confidence."""
    await seed_user("applicant_sneha", "Sneha Reddy")
    await seed_user("adm_admin_user3", "Admissions Admin 3", "admissions_admin")

    await seed_conversation_with_messages(
        "conv-transcript-1",
        "applicant_sneha",
        "admissions",
        "Status check",
        [
            {"sender": "user", "content": "What is the status of APP-1004?"},
            {
                "sender": "bot",
                "content": "Application APP-1004 is currently Rejected.",
                "intent_name": "check_application_status",
                "confidence": 0.96,
                "entities": {"application_id": "APP-1004"},
            },
        ],
    )

    async with _client() as client:
        res = await client.get(
            "/api/admin/conversations/conv-transcript-1/messages",
            headers=headers_for("adm_admin_user3", "admissions_admin"),
        )
        assert res.status_code == 200
        data = res.json()["data"]

        assert data["conversation_id"] == "conv-transcript-1"
        assert data["role_pack"] == "admissions"
        assert data["user_name"] == "Sneha Reddy"
        assert len(data["messages"]) == 2

        m_user = data["messages"][0]
        assert m_user["sender"] == "user"
        assert m_user["content"] == "What is the status of APP-1004?"
        assert m_user["intent_name"] is None

        m_bot = data["messages"][1]
        assert m_bot["sender"] == "bot"
        assert m_bot["content"] == "Application APP-1004 is currently Rejected."
        assert m_bot["intent_name"] == "check_application_status"
        assert m_bot["confidence"] == 0.96
        assert m_bot["entities"] == {"application_id": "APP-1004"}


# --- AC-3: Different role pack -> 403; missing ID -> 404 ---


@pytest.mark.asyncio
async def test_admin_transcript_cross_role_pack_forbidden_and_not_found():
    """Conversation in another role pack returns 403; missing ID returns 404."""
    await seed_user("emp_bob", "Bob Smith")
    await seed_user("adm_admin_user4", "Admissions Admin 4", "admissions_admin")

    # HR conversation
    await seed_conversation_with_messages(
        "conv-hr-secret",
        "emp_bob",
        "hr",
        "HR Secret Discussion",
        [{"sender": "user", "content": "HR policy question"}],
    )

    async with _client() as client:
        # Cross role pack access by Admissions admin -> 403
        res_cross = await client.get(
            "/api/admin/conversations/conv-hr-secret/messages",
            headers=headers_for("adm_admin_user4", "admissions_admin"),
        )
        assert res_cross.status_code == 403
        assert "Forbidden" in str(res_cross.json().get("error"))

        # Missing conversation ID -> 404
        res_missing = await client.get(
            "/api/admin/conversations/conv-does-not-exist-xyz/messages",
            headers=headers_for("adm_admin_user4", "admissions_admin"),
        )
        assert res_missing.status_code == 404
        assert "not found" in str(res_missing.json().get("error")).lower()


# --- N15 (slice-40) ---------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_conversations_filter_inclusive_to_date_and_actor_search():
    """N15: 'to' date is inclusive of today; actor search matches name and email."""
    now = datetime.utcnow()
    today_str = now.strftime("%Y-%m-%d")

    await seed_user("emp_deepa", "Deepa Krishnan", "end_user")
    await seed_conversation_with_messages(
        "conv-adm-today",
        "emp_deepa",
        "admissions",
        "Today inquiry",
        [{"sender": "user", "content": "When are classes?"}],
        created_at=now,
    )

    async with _client() as client:
        # Search with to=today includes today's conversation
        res_today = await client.get(
            f"/api/admin/conversations?to={today_str}",
            headers=headers_for("adm_admin_user", "admissions_admin"),
        )
        assert res_today.status_code == 200
        ids = [c["id"] for c in res_today.json()["data"]["conversations"]]
        assert "conv-adm-today" in ids

        # Search by actor name "Deepa"
        res_name = await client.get(
            "/api/admin/conversations?actor_id=Deepa",
            headers=headers_for("adm_admin_user", "admissions_admin"),
        )
        assert res_name.status_code == 200
        assert any(c["id"] == "conv-adm-today" for c in res_name.json()["data"]["conversations"])

        # Search by actor email "emp_deepa@test.com"
        res_email = await client.get(
            "/api/admin/conversations?actor_id=emp_deepa@test.com",
            headers=headers_for("adm_admin_user", "admissions_admin"),
        )
        assert res_email.status_code == 200
        assert any(c["id"] == "conv-adm-today" for c in res_email.json()["data"]["conversations"])
