import pytest
from unittest.mock import AsyncMock, patch

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.services.jwt_service import issue_token
from app.services import response_renderer
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from app.routers.chat import CLARIFICATION_PROMPT
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str):
    token = issue_token(user_id, "end_user", f"{user_id}@test.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


def rasa_payload(**overrides):
    base = {
        "intent": "check_leave_balance",
        "confidence": 0.95,
        "entities": {"employee_id": "EMP-1042"},
        "template_key": "check_leave_balance_response",
        "slots": {"balance": 12},
        "current_form": None,
        "current_step": None,
        "response_text": None,
    }
    base.update(overrides)
    return base


async def seed_template(template_key, variants, role_pack="hr"):
    async with TestingSessionLocal() as s:
        template = ResponseTemplate(
            role_pack=role_pack,
            template_key=template_key,
            base_text=variants[0],
            available_variables=[],
        )
        s.add(template)
        await s.flush()
        for text in variants:
            s.add(ResponseVariant(template_id=template.template_id, variant_text=text))
        await s.commit()


async def make_conversation(client, headers, role_pack="hr"):
    res = await client.post("/api/conversations", json={"role_pack": role_pack}, headers=headers)
    assert res.status_code == 201
    return res.json()["data"]["id"]


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_chat_returns_full_shape():
    """AC: 200 with response_text, intent, confidence, entities, session."""
    await seed_template(
        "check_leave_balance_response",
        ["You have {balance} days of leave remaining.", "Your balance is {balance} days."],
    )
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "What's my leave balance?"},
                headers=headers_for("u1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["intent"] == "check_leave_balance"
    assert data["confidence"] == 0.95
    assert data["entities"] == {"employee_id": "EMP-1042"}
    assert data["response_text"] in (
        "You have 12 days of leave remaining.",
        "Your balance is 12 days.",
    )
    assert set(data["session"].keys()) == {"current_form", "current_step", "slots"}


@pytest.mark.asyncio
async def test_chat_non_owner_forbidden():
    """AC: a non-owner gets 403."""
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("owner"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "hi"},
                headers=headers_for("intruder"),
            )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_chat_missing_conversation_not_found():
    """AC: a missing conversation gets 404."""
    async with _client() as client:
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": "does-not-exist", "message": "hi"},
                headers=headers_for("u1"),
            )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_chat_missing_message_unprocessable():
    """AC: a missing message gets 422."""
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        res = await client.post(
            "/api/chat",
            json={"conversation_id": conv_id},
            headers=headers_for("u1"),
        )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_multi_turn_slots_persist():
    """AC: session slots persist across turns (FR-4)."""
    await seed_template("leave_form_response", ["Got it."])
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))

        turn1 = rasa_payload(
            intent="request_leave",
            template_key="leave_form_response",
            slots={"leave_type": "casual"},
            current_form="leave_request_form",
            current_step="ask_dates",
        )
        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=turn1)):
            await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "I want casual leave"},
                headers=headers_for("u1"),
            )

        turn2 = rasa_payload(
            intent="request_leave",
            template_key="leave_form_response",
            slots={"start_date": "Sep 10"},
            current_form="leave_request_form",
            current_step="confirm",
        )
        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=turn2)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "Sep 10"},
                headers=headers_for("u1"),
            )

    slots = res.json()["data"]["session"]["slots"]
    assert slots.get("leave_type") == "casual"   # from turn 1
    assert slots.get("start_date") == "Sep 10"   # from turn 2
    assert res.json()["data"]["session"]["current_step"] == "confirm"


@pytest.mark.asyncio
async def test_low_confidence_returns_clarification():
    """AC: below-threshold top intent returns a clarification prompt, not a workflow (FR-2)."""
    await seed_template("check_leave_balance_response", ["You have {balance} days left."])
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        low = rasa_payload(confidence=0.15)
        with patch("app.services.dialogue_router._post_to_rasa", new=AsyncMock(return_value=low)):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "mumble mumble"},
                headers=headers_for("u1"),
            )

    data = res.json()["data"]
    assert data["response_text"] == CLARIFICATION_PROMPT
    # Did not render the workflow response.
    assert "days left" not in data["response_text"]
    # Session was not advanced into a form.
    assert data["session"]["current_form"] is None


@pytest.mark.asyncio
async def test_routes_to_matching_rasa_instance_only():
    """AC: the router forwards to the role pack's Rasa instance and no other."""
    await seed_template("check_ticket_status_response", ["Ticket is open."], role_pack="it")
    mock_post = AsyncMock(return_value=rasa_payload(
        intent="check_ticket_status", template_key="check_ticket_status_response", slots={},
    ))
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"), role_pack="it")
        with patch("app.services.dialogue_router._post_to_rasa", new=mock_post):
            await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "status of my ticket"},
                headers=headers_for("u1"),
            )

    called_url = mock_post.await_args.args[0]
    assert called_url.startswith(settings.RASA_IT_URL)
    assert not called_url.startswith(settings.RASA_HR_URL)
    assert not called_url.startswith(settings.RASA_ADMISSIONS_URL)


@pytest.mark.asyncio
async def test_renderer_substitutes_and_picks_a_stored_variant():
    """AC: renderer returns a stored variant at random with slots substituted."""
    await seed_template(
        "greeting_response",
        ["Hello {name}!", "Hi there {name}.", "Welcome, {name}."],
    )
    expected = {"Hello Priya!", "Hi there Priya.", "Welcome, Priya."}
    async with TestingSessionLocal() as s:
        for _ in range(12):
            out = await response_renderer.render(s, "greeting_response", {"name": "Priya"})
            assert out in expected


@pytest.mark.asyncio
async def test_renderer_returns_none_for_unknown_template():
    async with TestingSessionLocal() as s:
        assert await response_renderer.render(s, "no_such_template", {}) is None


# --- Talk mode (slice-06) ---------------------------------------------------


@pytest.mark.asyncio
async def test_talk_mode_returns_audio_when_tts_available():
    """AC: mode=talk with TTS available → audio_base64, audio_content_type, tts_available:true."""
    import base64

    await seed_template(
        "check_leave_balance_response",
        ["You have {balance} days of leave remaining."],
    )
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ), patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", "/fake/sa.json"), patch(
            "app.services.tts_service._synthesize_bytes", return_value=b"SPOKEN-AUDIO"
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "balance?", "mode": "talk"},
                headers=headers_for("u1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["tts_available"] is True
    assert data["audio_content_type"] == "audio/mp3"
    assert base64.b64decode(data["audio_base64"]) == b"SPOKEN-AUDIO"
    # The text reply is present alongside the audio.
    assert data["response_text"] == "You have 12 days of leave remaining."


@pytest.mark.asyncio
async def test_talk_mode_degrades_to_text_when_tts_fails():
    """AC: TTS failure/credits exhausted → tts_available:false, audio null, text still returned."""
    await seed_template(
        "check_leave_balance_response",
        ["You have {balance} days of leave remaining."],
    )
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ), patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", "/fake/sa.json"), patch(
            "app.services.tts_service._synthesize_bytes",
            side_effect=RuntimeError("credits exhausted"),
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "balance?", "mode": "talk"},
                headers=headers_for("u1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["tts_available"] is False
    assert data["audio_base64"] is None
    # No crash — the text reply is still delivered.
    assert data["response_text"] == "You have 12 days of leave remaining."


@pytest.mark.asyncio
async def test_chat_mode_has_no_audio_fields_populated():
    """Chat mode is unchanged: talk fields stay null (TTS is never invoked)."""
    await seed_template("check_leave_balance_response", ["You have {balance} days left."])
    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u1"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_payload()),
        ), patch("app.services.tts_service._synthesize_bytes") as seam:
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "balance?", "mode": "chat"},
                headers=headers_for("u1"),
            )

    data = res.json()["data"]
    assert data["tts_available"] is None
    assert data["audio_base64"] is None
    assert data["audio_content_type"] is None
    seam.assert_not_called()


@pytest.mark.asyncio
async def test_chat_records_audit_log_on_leave_submitted():
    """Slice-15 AC 5: Given a submission, an audit_log entry is written (FR-9, safety NFR)."""
    from sqlalchemy import select
    from app.models.audit_log import AuditLog

    await seed_template("submit_leave_result", ["Leave request submitted! Reference {reference_id}."])
    rasa_resp = rasa_payload(
        intent="submit_leave_request",
        template_key="submit_leave_result",
        slots={"reference_id": "LEAVE-9090", "leave_type": "casual"},
        audit_event={
            "action_type": "leave_submitted",
            "reference_id": "LEAVE-9090",
            "details": {"leave_type": "casual", "days": 2},
        },
    )

    async with _client() as client:
        conv_id = await make_conversation(client, headers_for("u-audit-1"))
        with patch(
            "app.services.dialogue_router._post_to_rasa",
            new=AsyncMock(return_value=rasa_resp),
        ):
            res = await client.post(
                "/api/chat",
                json={"conversation_id": conv_id, "message": "confirm", "mode": "chat"},
                headers=headers_for("u-audit-1"),
            )

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["session"]["slots"]["reference_id"] == "LEAVE-9090"

    # Verify audit_log entry in DB
    async with TestingSessionLocal() as s:
        stmt = select(AuditLog).where(
            AuditLog.reference_id == "LEAVE-9090",
            AuditLog.action_type == "leave_submitted",
        )
        entry = (await s.execute(stmt)).scalar_one_or_none()
        assert entry is not None
        assert entry.user_id == "u-audit-1"
        assert entry.role_pack == "hr"
        assert entry.details == {"leave_type": "casual", "days": 2}

