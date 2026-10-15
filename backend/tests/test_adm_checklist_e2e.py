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
        json={"role_pack": "admissions", "title": "Checklist Inquiry"},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["data"]["id"]


@pytest.mark.asyncio
async def test_adm_checklist_valid_flow_renders_list(db_session):
    """
    AC-1: Given a program, when the applicant asks for the document checklist,
    the bot returns the checklist as a list.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    docs = [
        "Class 10 Grade Sheet / Birth Certificate",
        "Class 12 / Higher Secondary Marksheet",
        "Entrance Exam Scorecard (JEE / CET)",
        "Transfer Certificate & Conduct Certificate",
        "Valid Government Photo ID",
    ]
    items_summary = ", ".join(docs)

    rasa_reply = {
        "intent": "get_document_checklist",
        "confidence": 0.95,
        "entities": {"program": "Computer Science (B.Tech)"},
        "template_key": "get_document_checklist_response",
        "slots": {
            "program": "Computer Science (B.Tech)",
            "required_documents": docs,
            "items_summary": items_summary,
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_chk_1"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "what documents do I need for btech?"},
                headers=headers_for("applicant_chk_1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "get_document_checklist"
    assert data["confidence"] >= 0.85
    assert data["entities"]["program"] == "Computer Science (B.Tech)"

    # Verify template rendered content has program name and document summary
    assert "Computer Science (B.Tech)" in data["response_text"]
    assert "Class 10 Grade Sheet" in data["response_text"]

    # Verify slots in session
    slots = data["session"]["slots"]
    assert slots["program"] == "Computer Science (B.Tech)"
    assert slots["required_documents"] == docs
    assert slots["found"] is True


@pytest.mark.asyncio
async def test_adm_checklist_missing_program_prompts_for_program(db_session):
    """
    AC-2: Given no program specified, the bot prompts for the program before answering (slot prompt).
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply_slot_prompt = {
        "intent": "get_document_checklist",
        "confidence": 0.90,
        "entities": {},
        "template_key": None,
        "slots": {},
        "current_form": "get_document_checklist_form",
        "current_step": "await_program",
        "response_text": "Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)",
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_chk_2"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply_slot_prompt)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "list of documents needed for admission"},
                headers=headers_for("applicant_chk_2"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "get_document_checklist"
    assert data["response_text"] == "Which program would you like the document checklist for? (e.g. B.Tech, M.Tech, MBA)"
    assert data["session"]["current_form"] == "get_document_checklist_form"
    assert data["session"]["current_step"] == "await_program"


@pytest.mark.asyncio
async def test_adm_checklist_unknown_program_graceful_not_found(db_session):
    """
    AC-3: Given an unknown program, the bot returns a graceful not-found (no crash).
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    rasa_reply_not_found = {
        "intent": "get_document_checklist",
        "confidence": 0.91,
        "entities": {"program": "Astrophysics"},
        "template_key": "get_document_checklist_not_found_response",
        "slots": {
            "program": "Astrophysics",
            "available_programs": ["Computer Science (B.Tech)", "Data Science (M.Tech)", "MBA"],
            "found": False,
        },
        "current_form": None,
        "current_step": None,
        "response_text": "No document checklist found for program 'Astrophysics'. Available programs: Computer Science (B.Tech), Data Science (M.Tech), MBA.",
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_chk_3"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply_not_found)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "what documents do I need for Astrophysics?"},
                headers=headers_for("applicant_chk_3"),
            )

    assert res.status_code == 200
    data = res.json()["data"]

    assert data["intent"] == "get_document_checklist"
    assert "Astrophysics" in data["response_text"]
    assert "Computer Science (B.Tech)" in data["response_text"]

    slots = data["session"]["slots"]
    assert slots["program"] == "Astrophysics"
    assert slots["found"] is False
    assert "available_programs" in slots


@pytest.mark.asyncio
async def test_adm_checklist_persisted_bot_message_records_intent_and_confidence(db_session):
    """
    AC-4: Given the bot response, the persisted bot message records the intent + confidence.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    docs = ["MBA Entrance Scorecard", "Degree Certificate", "SOP"]
    rasa_reply = {
        "intent": "get_document_checklist",
        "confidence": 0.94,
        "entities": {"program": "MBA"},
        "template_key": "get_document_checklist_response",
        "slots": {
            "program": "MBA",
            "required_documents": docs,
            "items_summary": ", ".join(docs),
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_chk_4"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "checklist of documents for mba"},
                headers=headers_for("applicant_chk_4"),
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
    assert bot_msg.intent_name == "get_document_checklist"
    assert bot_msg.confidence == 0.94
    assert bot_msg.entities == {"program": "MBA"}
    assert "MBA" in bot_msg.content
    assert "MBA Entrance Scorecard" in bot_msg.content


@pytest.mark.asyncio
async def test_adm_checklist_wording_varies_across_repeated_asks(db_session):
    """
    Verifies that response templates vary naturally across repeated queries.
    """
    await seed_admissions_data(db_session)
    await db_session.commit()

    docs = ["Doc A", "Doc B", "Doc C"]
    rasa_reply = {
        "intent": "get_document_checklist",
        "confidence": 0.95,
        "entities": {"program": "Data Science (M.Tech)"},
        "template_key": "get_document_checklist_response",
        "slots": {
            "program": "Data Science (M.Tech)",
            "required_documents": docs,
            "items_summary": ", ".join(docs),
            "found": True,
        },
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }

    responses_seen = set()

    async with _client() as client:
        conv_id = await make_admissions_conversation(client, headers_for("applicant_chk_5"))

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_reply)):
            for _ in range(15):
                res = await client.post(
                    "/api/chat",
                    json={"conversation_id": conv_id, "message": "what do I need to submit for Data Science?"},
                    headers=headers_for("applicant_chk_5"),
                )
                assert res.status_code == 200
                responses_seen.add(res.json()["data"]["response_text"])

    assert len(responses_seen) > 1, f"Expected multiple distinct variants, got: {responses_seen}"
    for text in responses_seen:
        assert "Data Science (M.Tech)" in text
        assert "Doc A, Doc B, Doc C" in text
