"""Tests for Slice 16: HR Policy FAQ.

Acceptance Criteria:
1. Given an HR policy question (e.g. "what's the WFH policy?"), when asked in an HR
   conversation, then the bot returns the policy answer via the FAQ-answer component.
2. Given an hr_admin, when they create a new static FAQ (name + phrases + response)
   in the console, then it is stored scoped to HR with needs_retrain: true.
3. Given a low-confidence policy question, then the bot asks for clarification
   rather than answering wrongly (FR-2 upstream).
4. Given the seed step, then the default HR policy FAQs exist and are visible
   in the HR admin Intent List.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.routers.chat import CLARIFICATION_PROMPT
from app.services.jwt_service import issue_token
from scripts.seed import seed_hr_data
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str, role: str = "end_user"):
    token = issue_token(user_id, role, f"{user_id}@test.com")
    return {"Authorization": f"Bearer {token}"}


HR_ADMIN = headers_for("anita_hr", "hr_admin")
USER = headers_for("u1", "end_user")


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


@pytest.mark.asyncio
async def test_ac4_default_hr_policy_faqs_exist_and_visible_in_admin_list(db_session):
    """AC 4: Given the seed step, default HR policy FAQs exist and are visible in HR admin Intent List."""
    await seed_hr_data(db_session)
    await db_session.commit()

    async with _client() as client:
        res = await client.get("/api/admin/intents", headers=HR_ADMIN)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["role_pack"] == "hr"
        intents = {item["name"]: item for item in data["intents"]}

        # Both default policy FAQs exist
        assert "ask_wfh_policy" in intents
        assert "ask_policy_faq" in intents

        wfh = intents["ask_wfh_policy"]
        assert wfh["intent_type"] == "static_faq"
        assert len(wfh["training_phrases"]) >= 5
        assert wfh["response_template"] is not None
        assert wfh["response_template"]["template_key"] == "ask_wfh_policy_response"
        assert "3 days per week" in wfh["response_template"]["base_text"]

        faq = intents["ask_policy_faq"]
        assert faq["intent_type"] == "static_faq"
        assert len(faq["training_phrases"]) >= 5
        assert faq["response_template"] is not None
        assert "20 annual leaves" in faq["response_template"]["base_text"]


@pytest.mark.asyncio
async def test_ac1_hr_wfh_policy_question_returns_policy_answer(db_session):
    """AC 1: Given an HR policy question (e.g. 'what's the WFH policy?'), returns policy answer."""
    await seed_hr_data(db_session)
    await db_session.commit()

    async with _client() as client:
        # Create conversation
        conv_res = await client.post("/api/conversations", json={"role_pack": "hr"}, headers=USER)
        assert conv_res.status_code == 201
        conv_id = conv_res.json()["data"]["id"]

        # Mock Rasa converse response for ask_wfh_policy
        rasa_return = {
            "intent": "ask_wfh_policy",
            "confidence": 0.95,
            "entities": {},
            "template_key": "ask_wfh_policy_response",
            "slots": {"is_faq": True, "intent_type": "static_faq"},
            "current_form": None,
            "current_step": None,
            "response_text": "Employees may work from home up to 3 days per week, subject to manager approval.",
        }

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_return)):
            chat_res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "What's the WFH policy?"},
                headers=USER,
            )

        assert chat_res.status_code == 200
        data = chat_res.json()["data"]
        assert data["intent"] == "ask_wfh_policy"
        assert data["confidence"] == 0.95
        assert data["session"]["slots"].get("is_faq") is True
        assert any(
            phrase in data["response_text"].lower()
            for phrase in ["work from home", "3 days", "wfh", "remotely"]
        )


@pytest.mark.asyncio
async def test_ac2_hr_admin_create_static_faq(db_session):
    """AC 2: Given an hr_admin, when creating a new static FAQ, it is stored scoped to HR with needs_retrain: true."""
    async with _client() as client:
        body = {
            "name": "ask_dress_code_policy",
            "training_phrases": [
                "what is the company dress code?",
                "is casual dress allowed?",
                "what should I wear to work?",
            ],
            "response_template": {
                "base_text": "Our dress code is business casual Monday through Thursday, and smart casual on Fridays.",
                "allow_rephrasing": True,
            },
        }
        res = await client.post("/api/admin/intents", headers=HR_ADMIN, json=body)
        assert res.status_code == 201
        data = res.json()["data"]["intent"]

        assert data["name"] == "ask_dress_code_policy"
        assert data["role_pack"] == "hr"
        assert data["intent_type"] == "static_faq"
        assert data["needs_retrain"] is True
        assert len(data["training_phrases"]) == 3
        assert data["response_template"]["available_variables"] == []
        assert "business casual" in data["response_template"]["base_text"]


@pytest.mark.asyncio
async def test_ac3_low_confidence_policy_question_clarification(db_session):
    """AC 3: Low-confidence policy question returns clarification prompt rather than answering wrongly."""
    await seed_hr_data(db_session)
    await db_session.commit()

    async with _client() as client:
        conv_res = await client.post("/api/conversations", json={"role_pack": "hr"}, headers=USER)
        assert conv_res.status_code == 201
        conv_id = conv_res.json()["data"]["id"]

        # Low-confidence Rasa response (below 0.4 threshold)
        rasa_low = {
            "intent": "ask_wfh_policy",
            "confidence": 0.25,
            "entities": {},
            "template_key": "ask_wfh_policy_response",
            "slots": {},
            "current_form": None,
            "current_step": None,
            "response_text": None,
        }

        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=rasa_low)):
            chat_res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "vague confusing policy query"},
                headers=USER,
            )

        assert chat_res.status_code == 200
        data = chat_res.json()["data"]
        # Must return clarification prompt
        assert data["response_text"] == CLARIFICATION_PROMPT
        # Must NOT render the policy response
        assert "days per week" not in data["response_text"]
