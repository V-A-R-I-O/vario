import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.models.message import Message
from app.services.jwt_service import issue_token
from scripts.seed import seed_admissions_data
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
    res = await client.post(
        "/api/conversations",
        json={"role_pack": "admissions", "title": "Fees and Deadlines Inquiry"},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_adm_fee_query_renders_calendar_fee(db_session):
    """
    AC-1: Given a fee question, return fee from calendar.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    fees = [{"item": "Computer Science (B.Tech) Annual Tuition", "amount": "₹3,20,000"}]
    details = "Computer Science (B.Tech) Annual Tuition: ₹3,20,000"

    rasa_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.95,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "fee",
            "details": details,
            "fees": fees,
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_fee_1"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "how much is the tuition fee for B.Tech?"},
                headers=headers_for("applicant_fee_1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "ask_fee_deadline"
    assert data["confidence"] >= 0.85
    assert "2026-2027" in data["response_text"]
    assert "₹3,20,000" in data["response_text"]

    slots = data["session"]["slots"]
    assert slots["academic_year"] == "2026-2027"
    assert slots["topic"] == "fee"
    assert slots["fees"] == fees
    assert slots["found"] is True


@pytest.mark.asyncio
async def test_adm_deadline_query_renders_calendar_deadline(db_session):
    """
    AC-2: Given a deadline question, return relevant deadline from calendar.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    deadlines = [{"milestone": "Regular Application Submission Deadline", "date": "November 30, 2026"}]
    details = "Regular Application Submission Deadline: November 30, 2026"

    rasa_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.94,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "deadline",
            "details": details,
            "deadlines": deadlines,
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_dl_1"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "what is the last date to submit the application?"},
                headers=headers_for("applicant_dl_1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "ask_fee_deadline"
    assert data["confidence"] >= 0.85
    assert "2026-2027" in data["response_text"]
    assert "November 30, 2026" in data["response_text"]

    slots = data["session"]["slots"]
    assert slots["academic_year"] == "2026-2027"
    assert slots["topic"] == "deadline"
    assert slots["deadlines"] == deadlines


@pytest.mark.asyncio
async def test_adm_calendar_dynamic_update_changes_answers(db_session):
    """
    AC-3: Given a change to calendar (in Mock Admissions), answers update accordingly.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    initial_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.95,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "deadline",
            "details": "Regular Application Submission Deadline: November 30, 2026",
            "deadlines": [{"milestone": "Regular Application Submission Deadline", "date": "November 30, 2026"}],
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    updated_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.95,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "deadline",
            "details": "Regular Application Submission Deadline: December 15, 2026 (Extended)",
            "deadlines": [{"milestone": "Regular Application Submission Deadline", "date": "December 15, 2026 (Extended)"}],
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_cal_dyn"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=initial_reply)):
            res1 = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "what is the last date to submit the application?"},
                headers=headers_for("applicant_cal_dyn"),
            )
            assert res1.status_code == 200
            assert "November 30, 2026" in res1.json()["data"]["response_text"]

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=updated_reply)):
            res2 = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "what is the last date to submit the application?"},
                headers=headers_for("applicant_cal_dyn"),
            )
            assert res2.status_code == 200
            assert "December 15, 2026 (Extended)" in res2.json()["data"]["response_text"]


@pytest.mark.asyncio
async def test_adm_vague_or_low_confidence_requests_clarification(db_session):
    """
    AC-4: Given a low-confidence question, ask for clarification rather than guessing.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    clarification_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.60,
        "entities": {},
        "template_key": None,
        "slots": {},
        "current_form": None,
        "current_step": None,
        "response_text": "Could you please clarify whether you are asking about tuition fees, application fees, or application and payment deadlines?",
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_vague_1"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=clarification_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "when?"},
                headers=headers_for("applicant_vague_1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "ask_fee_deadline"
    assert "Could you please clarify" in data["response_text"]


@pytest.mark.asyncio
async def test_adm_fee_deadline_persisted_bot_message_records_intent_and_confidence(db_session):
    """
    Verifies that the bot message records intent_name + confidence when saved to the database.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    fees = [{"item": "MBA Annual Tuition", "amount": "₹4,50,000"}]
    details = "MBA Annual Tuition: ₹4,50,000"

    rasa_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.93,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "fee",
            "details": details,
            "fees": fees,
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_db_fee"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "tuition fee for MBA program"},
                headers=headers_for("applicant_db_fee"),
            )

    assert res.status_code == 200

    async with TestingSessionLocal() as s:
        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_id, Message.sender == "bot")
            .order_by(Message.created_at.desc())
        )
        bot_msg = (await s.execute(stmt)).scalars().first()

    assert bot_msg is not None
    assert bot_msg.sender == "bot"
    assert bot_msg.intent_name == "ask_fee_deadline"
    assert bot_msg.confidence == 0.93
    assert "₹4,50,000" in bot_msg.content
    assert "2026-2027" in bot_msg.content


@pytest.mark.asyncio
async def test_adm_fee_deadline_wording_varies_across_repeated_asks(db_session):
    """
    Verifies that response templates vary naturally across repeated queries.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply = {
        "intent": "ask_fee_deadline",
        "confidence": 0.95,
        "entities": {},
        "template_key": "ask_fee_deadline_response",
        "slots": {
            "academic_year": "2026-2027",
            "topic": "fee",
            "details": "Application Fee: ₹1,500 (Non-refundable)",
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    responses_seen = set()

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_var_fee"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            for _ in range(15):
                res = await client.post(
                    "/api/chat",
                    json={"conversation_id": conv_id, "message": "what is the application fee?"},
                    headers=headers_for("applicant_var_fee"),
                )
                assert res.status_code == 200
                responses_seen.add(res.json()["data"]["response_text"])

    assert len(responses_seen) > 1, f"Expected multiple distinct variants, got: {responses_seen}"
    for text in responses_seen:
        assert "2026-2027" in text
        assert "Application Fee: ₹1,500 (Non-refundable)" in text
