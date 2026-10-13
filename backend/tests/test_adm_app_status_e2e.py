import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.models.message import Message
from app.services.jwt_service import issue_token
from scripts.seed import seed_admissions_data, ADMISSIONS_STATUS_VARIANTS, ADMISSIONS_NOT_FOUND_VARIANTS
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str, role: str = "end_user"):
    token = issue_token(user_id, role, f"{user_id}@admissions.test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def make_admissions_conversation(client, headers):
    res = await client.post("/api/conversations", json={"role_pack": "admissions", "title": "Application Status Inquiry"}, headers=headers)
    assert res.status_code == 201
    return res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_adm_app_status_valid_flow_renders_status_and_next_step(db_session):
    """
    AC 1: Given a logged-in applicant in an Admissions conversation,
    when they ask for a valid application's status, then status + next step are returned.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply = {
        "intent": "check_application_status",
        "confidence": 0.95,
        "entities": {"application_id": "APP-1001"},
        "template_key": "check_application_status_response",
        "slots": {
            "application_id": "APP-1001",
            "status": "Under Review",
            "next_step": "Document verification in progress. Decision expected by Nov 15.",
            "applicant_name": "Aarav Sharma",
            "program": "B.Tech Computer Science",
            "fee_status": "Paid",
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_1"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "What is the status of application APP-1001?"},
                headers=headers_for("applicant_1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    # Verify intent, confidence, entities
    assert data["intent"] == "check_application_status"
    assert data["confidence"] >= 0.85
    assert data["entities"]["application_id"] == "APP-1001"

    # Verify response_text has status and next step substituted
    assert "APP-1001" in data["response_text"]
    assert "Under Review" in data["response_text"]
    assert "Document verification in progress" in data["response_text"]

    # Verify slots in session
    slots = data["session"]["slots"]
    assert slots["application_id"] == "APP-1001"
    assert slots["status"] == "Under Review"
    assert "next_step" in slots


@pytest.mark.asyncio
async def test_adm_app_status_unknown_id_graceful_not_found(db_session):
    """
    AC 2: Given an unknown application id, then the bot returns a graceful "not found"
    with a suggested next step (FR-17) — no crash.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply_not_found = {
        "intent": "check_application_status",
        "confidence": 0.95,
        "entities": {"application_id": "APP-9999"},
        "template_key": "check_application_status_not_found_response",
        "slots": {
            "application_id": "APP-9999",
            "status": "Not Found",
            "suggested_next_step": "Please verify your application ID or contact admissions@org.example.com.",
            "found": False,
        },
        "current_form": None,
        "current_step": None,
        "response_text": "Application APP-9999 was not found. Suggested next step: Please verify your application ID or contact admissions@org.example.com.",
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_2"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply_not_found)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "Can you check status of APP-9999?"},
                headers=headers_for("applicant_2"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "check_application_status"
    assert data["confidence"] >= 0.85
    assert "APP-9999" in data["response_text"]
    assert "admissions@org.example.com" in data["response_text"]

    slots = data["session"]["slots"]
    assert slots["status"] == "Not Found"
    assert "suggested_next_step" in slots
    assert "admissions@org.example.com" in slots["suggested_next_step"]


@pytest.mark.asyncio
async def test_adm_app_status_persisted_bot_message_records_intent_and_confidence(db_session):
    """
    AC 3: Given the bot response, then the persisted bot message records
    intent_name = check_application_status and a confidence.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply = {
        "intent": "check_application_status",
        "confidence": 0.92,
        "entities": {"application_id": "APP-1002"},
        "template_key": "check_application_status_response",
        "slots": {
            "application_id": "APP-1002",
            "status": "Documents Pending",
            "next_step": "Submit official B.Tech degree certificate and transcripts.",
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_3"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "status of APP-1002"},
                headers=headers_for("applicant_3"),
            )

    assert res.status_code == 200

    # Query the messages table in the DB
    async with TestingSessionLocal() as s:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id, Message.sender == "bot")
            .order_by(Message.created_at.desc())
        )
        bot_msg = (await s.execute(stmt)).scalars().first()

    assert bot_msg is not None
    assert bot_msg.sender == "bot"
    assert bot_msg.intent_name == "check_application_status"
    assert bot_msg.confidence == 0.92
    assert bot_msg.entities == {"application_id": "APP-1002"}
    assert "APP-1002" in bot_msg.content
    assert "Documents Pending" in bot_msg.content


@pytest.mark.asyncio
async def test_adm_app_status_wording_varies_across_repeated_asks(db_session):
    """
    AC 4: Given repeated asks, then wording varies (renderer picks a random variant).
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply = {
        "intent": "check_application_status",
        "confidence": 0.95,
        "entities": {"application_id": "APP-1003"},
        "template_key": "check_application_status_response",
        "slots": {
            "application_id": "APP-1003",
            "status": "Admitted",
            "next_step": "Pay acceptance fee of ₹50,000 before Oct 25 to confirm seat.",
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    responses_seen = set()

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_4"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            # Repeat request 15 times to observe variant picking
            for _ in range(15):
                res = await client.post(
                    "/api/chat",
                    json={"conversation_id": conv_id, "message": "what is happening with APP-1003?"},
                    headers=headers_for("applicant_4"),
                )
                assert res.status_code == 200
                responses_seen.add(res.json()["data"]["response_text"])

    # Across 15 samples with 5 distinct variants, multiple variants must be picked
    assert len(responses_seen) > 1, f"Expected multiple distinct variants, but got: {responses_seen}"
    for text in responses_seen:
        assert "APP-1003" in text
        assert "Admitted" in text


@pytest.mark.asyncio
async def test_adm_routes_strictly_to_admissions_rasa_port():
    """
    Verifies that dialogue_router strictly dispatches Admissions conversations to RASA_ADMISSIONS_URL.
    """
    mock_post = AsyncMock(
        return_value={
            "intent": "check_application_status",
            "confidence": 0.95,
            "entities": {"application_id": "APP-1001"},
            "template_key": None,
            "slots": {},
            "current_form": None,
            "current_step": None,
            "response_text": "Routed correctly",
        }
    )

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_5"))
        with patch("app.services.dialogue_router._post_to_rasa", new=mock_post):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "status of APP-1001"},
                headers=headers_for("applicant_5"),
            )

    assert res.status_code == 200
    called_url = mock_post.await_args.args[0]
    assert called_url.startswith(settings.RASA_ADMISSIONS_URL)
    assert not called_url.startswith(settings.RASA_HR_URL)
    assert not called_url.startswith(settings.RASA_IT_URL)
