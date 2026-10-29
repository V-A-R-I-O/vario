"""Gateway behaviour for the Rasa converse contract v2 (slice-32, ADR-006).

Role-pack replies come from the shared fixtures in rasa-shared/contract/, the
same files the Rasa channel tests and the role packs build against.
"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.message import Message
from app.models.session import Session
from app.models.user import User
from app.routers.chat import CLARIFICATION_PROMPT, REDACTED_CONTENT, degraded_reply
from app.services import dialogue_router
from app.services.jwt_service import issue_token
from tests.conftest import TestingSessionLocal

CONTRACT_DIR = Path(__file__).resolve().parents[2] / "rasa-shared" / "contract"
ORIGIN = {"Origin": "http://localhost:3000"}
POST_TO_RASA = "app.services.dialogue_router._post_to_rasa"


def contract(name):
    return json.loads((CONTRACT_DIR / name).read_text(encoding="utf-8"))


def reply(base="converse-response-card-turn.json", **overrides):
    payload = contract(base)
    payload.update(overrides)
    return payload


def headers_for(user_id):
    return {"Authorization": f"Bearer {issue_token(user_id, 'end_user', f'{user_id}@test.com')}"}


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _conversation(client, user_id, role_pack="hr"):
    res = await client.post("/api/conversations", json={"role_pack": role_pack}, headers=headers_for(user_id))
    assert res.status_code == 201
    return res.json()["data"]["id"]


async def _say(client, user_id, conv_id, message, rasa_reply=None, **patch_kwargs):
    mock = AsyncMock(return_value=rasa_reply, **patch_kwargs)
    with patch(POST_TO_RASA, new=mock):
        res = await client.post(
            "/api/chat",
            json={"conversation_id": conv_id, "message": message},
            headers={**headers_for(user_id), **ORIGIN},
        )
    return res, mock


async def _user_messages(conv_id):
    async with TestingSessionLocal() as db:
        rows = await db.execute(
            select(Message).where(Message.conversation_id == conv_id, Message.sender == "user")
            .order_by(Message.created_at)
        )
        return [m.content for m in rows.scalars().all()]


def test_card_types_match_the_shared_contract():
    assert dialogue_router.CARD_TYPES == frozenset(contract("card-types.json"))


@pytest.mark.asyncio
async def test_request_uses_conversation_id_and_trusted_identity():
    async with TestingSessionLocal() as db:
        db.add(User(user_id="u-emp", email="emp1@org.example.com", full_name="Employee One",
                    role="end_user", external_id="EMP-1001"))
        await db.commit()

    async with _client() as client:
        conv_id = await _conversation(client, "u-emp")
        res, mock = await _say(client, "u-emp", conv_id, "What's my leave balance?", reply())

    assert res.status_code == 200
    sent = mock.await_args.args[1]
    assert set(sent) == set(contract("converse-request.json"))
    assert sent["sender"] == conv_id
    assert sent["metadata"]["auth_context"]["employee_id"] == "EMP-1001"
    assert sent["metadata"]["user_id"] == "u-emp"
    assert sent["metadata"]["sensitive"] is False
    assert sent["auth_context"]["employee_id"] == "EMP-1001"  # deprecated copy for the v1 IT pack


@pytest.mark.asyncio
async def test_slots_from_an_earlier_turn_do_not_linger():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        await _say(client, "u1", conv_id, "leave balance for EMP-1042",
                   reply(slots={"total": 22, "employee_id": "EMP-1042"}))
        res, _ = await _say(client, "u1", conv_id, "can I work from home?",
                            reply(intent="ask_wfh_policy", template_key=None, slots={}, card=None,
                                  response_text="Up to 3 days a week."))

    assert res.json()["data"]["session"]["slots"] == {}


@pytest.mark.asyncio
async def test_card_is_returned_and_kept_in_history():
    card = contract("converse-response-card-turn.json")["card"]
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        res, _ = await _say(client, "u1", conv_id, "What's my leave balance?", reply())
        history = await client.get(f"/api/conversations/{conv_id}/messages", headers=headers_for("u1"))

    assert res.json()["data"]["card"] == card
    messages = history.json()["data"]["messages"]
    assert [m["sender"] for m in messages] == ["user", "bot"]
    assert messages[0]["card"] is None
    assert messages[1]["card"] == card


@pytest.mark.asyncio
async def test_unknown_card_type_is_dropped():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        res, _ = await _say(client, "u1", conv_id, "balance", reply(card={"type": "leave_balance_card"}))

    assert res.status_code == 200
    assert res.json()["data"]["card"] is None


@pytest.mark.asyncio
async def test_low_confidence_answer_inside_a_form_is_not_overridden():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        await _say(client, "u1", conv_id, "I want to apply for leave", reply("converse-response-form-turn.json"))
        res, _ = await _say(client, "u1", conv_id, "fever",
                            reply("converse-response-form-turn.json", intent="inform", confidence=0.12,
                                  current_step="start_date", card=None, response_text="When does it start?"))

    data = res.json()["data"]
    assert data["response_text"] == "When does it start?"
    assert data["session"]["current_step"] == "start_date"


@pytest.mark.asyncio
async def test_low_confidence_outside_a_form_still_clarifies():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        res, _ = await _say(client, "u1", conv_id, "blorp", reply(intent="nlu_fallback", confidence=0.2))

    assert res.json()["data"]["response_text"] == CLARIFICATION_PROMPT
    assert res.json()["data"]["card"] is None


@pytest.mark.asyncio
async def test_sensitive_flag_redacts_only_the_next_user_message():
    async with _client() as client:
        conv_id = await _conversation(client, "u1", role_pack="it")
        await _say(client, "u1", conv_id, "I forgot my password", reply("converse-response-sensitive-turn.json"))
        _, mock = await _say(client, "u1", conv_id, "sunrise",
                             reply("converse-response-sensitive-turn.json", current_form=None, current_step=None,
                                   sensitive_next_input=False, response_text="Password reset initiated."))
        await _say(client, "u1", conv_id, "thanks", reply(intent="goodbye", card=None))

    assert mock.await_args.args[1]["metadata"]["sensitive"] is True
    assert mock.await_args.args[1]["message"] == "sunrise"  # the pack still gets the real answer
    assert await _user_messages(conv_id) == ["I forgot my password", REDACTED_CONTENT, "thanks"]


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("timed out"),
        httpx.HTTPStatusError("boom", request=httpx.Request("POST", "http://rasa"),
                              response=httpx.Response(502)),
        ValueError("invalid JSON"),
    ],
)
@pytest.mark.asyncio
async def test_unreachable_role_pack_degrades_gracefully(error):
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        await _say(client, "u1", conv_id, "I want to apply for leave", reply("converse-response-form-turn.json"))
        res, _ = await _say(client, "u1", conv_id, "sick", side_effect=error)

    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
    data = res.json()["data"]
    assert data["degraded"] is True
    assert data["response_text"] == degraded_reply("hr")
    assert data["card"] == {"type": "error", "text": degraded_reply("hr")}
    assert data["session"]["current_form"] == "leave_request_form"  # dialogue not advanced
    assert await _user_messages(conv_id) == ["I want to apply for leave", "sick"]


@pytest.mark.asyncio
async def test_unhandled_error_returns_500_with_cors_headers():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        with patch("app.services.response_renderer.render", new=AsyncMock(side_effect=RuntimeError("bug"))):
            res, _ = await _say(client, "u1", conv_id, "balance", reply())

    assert res.status_code == 500
    assert res.json() == {"status": "error", "data": None, "error": "Internal server error"}
    assert "access-control-allow-origin" in res.headers


@pytest.mark.asyncio
async def test_expired_session_starts_fresh():
    async with _client() as client:
        conv_id = await _conversation(client, "u1")
        await _say(client, "u1", conv_id, "I want to apply for leave",
                   reply("converse-response-form-turn.json", slots={"leave_type": "sick"}))
        async with TestingSessionLocal() as db:
            session = (await db.execute(select(Session).where(Session.conversation_id == conv_id))).scalar_one()
            session.expires_at = datetime.utcnow() - timedelta(minutes=1)
            await db.commit()
        _, mock = await _say(client, "u1", conv_id, "hello", reply(intent="greet", card=None))

    assert mock.await_args.args[1]["session"] == {"current_form": None, "current_step": None, "slots": {}}
