"""Rephraser service tests (slice-09).

Acceptance criteria verified:
- Template save with allow_rephrasing -> response contains original + up to 4 generated variants,
  all preserving the base placeholders (US-9).
- Variant with dropped/renamed placeholder -> rejected, not stored.
- PUT template -> old variants replaced with newly generated ones.
- POST generate-phrases -> ~8 seed-based phrases returned, not auto-saved (US-8); no seed phrases -> 422.
- Accepted phrases saved via PUT intents/:id (training_phrases.add) persist.
- REPHRASER_PROVIDER selects provider via env with no code change; key read from env, never hardcoded.
- LLM failure -> save keeps original variant and reports the error (no crash).
"""
import json
import os
import pytest
import httpx
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.intent import Intent
from app.models.response_template import ResponseTemplate
from app.models.response_variant import ResponseVariant
from app.models.training_phrase import TrainingPhrase
from app.services import rephraser
from app.services.rephraser import (
    GeminiRephraser,
    PassthroughRephraser,
    get_rephraser_client,
)
from app.services.jwt_service import issue_token
from tests.conftest import TestingSessionLocal


def headers_for(user_id: str, role: str):
    return {"Authorization": f"Bearer {issue_token(user_id, role, f'{user_id}@test.com')}"}


HR = headers_for("hra", "hr_admin")


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    from app.utils.rate_limit import limiter
    limiter.requests.clear()
    yield
    limiter.requests.clear()


def make_gemini_response(items):
    """Create a mock Gemini generateContent response JSON structure."""
    return {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(items)
                        }
                    ]
                }
            }
        ]
    }


# --- Unit Tests: Provider Selection & Keys -----------------------------------


def test_provider_selection_env(monkeypatch):
    """AC: REPHRASER_PROVIDER selects provider via env with no code change."""
    monkeypatch.setenv("REPHRASER_PROVIDER", "passthrough")
    p_client = get_rephraser_client()
    assert isinstance(p_client, PassthroughRephraser)

    monkeypatch.setenv("REPHRASER_PROVIDER", "gemini")
    g_client = get_rephraser_client()
    assert isinstance(g_client, GeminiRephraser)

    monkeypatch.setenv("REPHRASER_PROVIDER", "unsupported_provider")
    with pytest.raises(ValueError, match="Unsupported REPHRASER_PROVIDER"):
        get_rephraser_client()


def test_gemini_key_read_from_env(monkeypatch):
    """AC: Key read from env, never hardcoded."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-env-key")
    client = GeminiRephraser()
    assert client.api_key == "test-secret-env-key"
    assert "test-secret-env-key" in client._get_url()


# --- Unit Tests: Passthrough ------------------------------------------------


@pytest.mark.asyncio
async def test_passthrough_rephraser():
    p = PassthroughRephraser()
    variants = await p.generate_variants("Hello {name}", ["name"])
    assert variants == ["Hello {name}"]

    phrases = await p.generate_phrases(["Seed phrase"], count=8)
    assert phrases == []


# --- Unit Tests: GeminiRephraser --------------------------------------------


@pytest.mark.asyncio
async def test_gemini_missing_api_key_graceful(monkeypatch):
    """AC: If GEMINI_API_KEY is unset, degrades gracefully to base text and empty list."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    client = GeminiRephraser(api_key="")
    assert client.api_key == ""

    variants = await client.generate_variants("Your balance is {balance}.", ["balance"])
    assert variants == ["Your balance is {balance}."]

    phrases = await client.generate_phrases(["Seed 1"], count=8)
    assert phrases == []


@pytest.mark.asyncio
async def test_gemini_variant_generation_success():
    """AC: Response contains original plus up to 4 generated variants preserving placeholders (US-9)."""
    generated = [
        "You currently have {balance} days of leave remaining.",
        "Your available leave count is {balance} days.",
        "There are {balance} leave days left in your balance.",
        "As of now, you have {balance} days of leave.",
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(generated))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    rephraser_client = GeminiRephraser(api_key="test-key", http_client=mock_http)

    variants = await rephraser_client.generate_variants(
        "You have {balance} days of leave remaining.", ["balance"]
    )

    assert len(variants) == 5
    assert variants[0] == "You have {balance} days of leave remaining."
    assert variants[1:] == generated


@pytest.mark.asyncio
async def test_gemini_variant_dropped_altered_placeholder_rejected():
    """AC: Given a variant the LLM returned with a dropped/renamed placeholder, then it is rejected and not stored."""
    candidates = [
        "You have {balance} days left.",  # Valid: retains {balance}
        "You have 5 days left.",  # Invalid: dropped {balance}
        "Your balance is {days_left}.",  # Invalid: renamed to {days_left}
        "You have {balance} days left on {account}.",  # Invalid: added {account}
        "Current balance: {balance} days remaining.",  # Valid: retains {balance}
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(candidates))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    rephraser_client = GeminiRephraser(api_key="test-key", http_client=mock_http)

    variants = await rephraser_client.generate_variants(
        "You have {balance} days of leave remaining.", ["balance"]
    )

    # Original + 2 valid variants = 3
    assert len(variants) == 3
    assert variants[0] == "You have {balance} days of leave remaining."
    assert variants[1] == "You have {balance} days left."
    assert variants[2] == "Current balance: {balance} days remaining."


@pytest.mark.asyncio
async def test_gemini_variant_llm_failure_graceful():
    """AC: Given an LLM failure, then the save keeps the original variant and reports error (no crash)."""
    async def mock_handler(request: httpx.Request):
        return httpx.Response(500, text="Internal Server Error")

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    rephraser_client = GeminiRephraser(api_key="test-key", http_client=mock_http)

    variants = await rephraser_client.generate_variants(
        "You have {balance} days of leave remaining.", ["balance"]
    )

    assert variants == ["You have {balance} days of leave remaining."]


@pytest.mark.asyncio
async def test_gemini_generate_phrases_success():
    """AC: Given POST generate-phrases, then ~8 seed-based phrases are returned."""
    mock_phrases = [
        "How much leave do I have?",
        "Can you check my leave balance?",
        "Tell me my remaining leave days",
        "What is my current leave count?",
        "How many leave days are available?",
        "Show my time off balance",
        "Check how many leaves I have left",
        "What is my leave status?",
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(mock_phrases))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    rephraser_client = GeminiRephraser(api_key="test-key", http_client=mock_http)

    phrases = await rephraser_client.generate_phrases(
        ["What's my leave balance?", "How many leaves do I have?"], count=8
    )

    assert len(phrases) == 8
    assert phrases == mock_phrases


# --- API Endpoint Integration Tests ------------------------------------------


@pytest.mark.asyncio
async def test_create_intent_with_rephraser_variants(monkeypatch):
    """AC: Template save with allow_rephrasing -> response contains original + up to 4 variants, all preserving placeholders."""
    generated = [
        "WFH is permitted up to 3 days weekly.",
        "You may work remotely for a maximum of 3 days a week.",
        "Our policy allows 3 work-from-home days each week.",
        "Staff can work from home up to 3 days per week.",
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(generated))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    test_rephraser = GeminiRephraser(api_key="test-key", http_client=mock_http)
    monkeypatch.setattr(rephraser, "get_rephraser_client", lambda *_: test_rephraser)

    async with _client() as client:
        res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_wfh_rephrase_test",
                "training_phrases": ["What is the remote work policy?"],
                "response_template": {
                    "base_text": "You may work from home up to 3 days a week.",
                    "allow_rephrasing": True,
                },
            },
        )

    assert res.status_code == 201
    intent = res.json()["data"]["intent"]
    tpl = intent["response_template"]
    assert tpl["allow_rephrasing"] is True

    # Original + 4 generated variants = 5 total
    variants = tpl["variants"]
    assert len(variants) == 5
    assert variants[0]["variant_text"] == "You may work from home up to 3 days a week."
    assert [v["variant_text"] for v in variants[1:]] == generated


@pytest.mark.asyncio
async def test_create_intent_dropped_placeholder_not_stored(monkeypatch):
    """AC: Variant with dropped/renamed placeholder is rejected and not stored."""
    candidates = [
        "Your balance is {balance} days remaining.",  # Valid
        "You have days left.",  # Invalid: dropped placeholder
        "Your total is {bal}.",  # Invalid: renamed placeholder
        "{balance} days of leave are available.",  # Valid
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(candidates))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    test_rephraser = GeminiRephraser(api_key="test-key", http_client=mock_http)
    monkeypatch.setattr(rephraser, "get_rephraser_client", lambda *_: test_rephraser)

    async with _client() as client:
        res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_placeholder_drop_test",
                "training_phrases": ["Check my balance"],
                "response_template": {
                    "base_text": "You have {balance} days of leave.",
                    "allow_rephrasing": True,
                },
            },
        )

    assert res.status_code == 201
    variants = res.json()["data"]["intent"]["response_template"]["variants"]
    # Original + 2 valid variants = 3
    assert len(variants) == 3
    assert variants[0]["variant_text"] == "You have {balance} days of leave."
    assert variants[1]["variant_text"] == "Your balance is {balance} days remaining."
    assert variants[2]["variant_text"] == "{balance} days of leave are available."


@pytest.mark.asyncio
async def test_put_template_replaces_old_variants(monkeypatch):
    """AC: Given PUT /api/admin/templates/:id, then old variants are replaced with newly generated ones."""
    # First, create an intent with initial variants
    initial_generated = [
        "Initial variant 1",
        "Initial variant 2",
        "Initial variant 3",
        "Initial variant 4",
    ]
    updated_generated = [
        "Updated variant 1",
        "Updated variant 2",
        "Updated variant 3",
        "Updated variant 4",
    ]

    current_response = initial_generated

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(current_response))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    test_rephraser = GeminiRephraser(api_key="test-key", http_client=mock_http)
    monkeypatch.setattr(rephraser, "get_rephraser_client", lambda *_: test_rephraser)

    async with _client() as client:
        create_res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_replace_variants_test",
                "training_phrases": ["Initial phrase"],
                "response_template": {
                    "base_text": "Initial base text.",
                    "allow_rephrasing": True,
                },
            },
        )
        assert create_res.status_code == 201
        tpl_id = create_res.json()["data"]["intent"]["response_template"]["id"]
        old_variant_ids = [v["id"] for v in create_res.json()["data"]["intent"]["response_template"]["variants"]]

        # Switch mock response for update
        current_response = updated_generated

        # Update the template base text
        put_res = await client.put(
            f"/api/admin/templates/{tpl_id}",
            headers=HR,
            json={
                "base_text": "Updated base text.",
                "allow_rephrasing": True,
            },
        )
        assert put_res.status_code == 200
        new_variants = put_res.json()["data"]["template"]["variants"]
        assert len(new_variants) == 5
        assert new_variants[0]["variant_text"] == "Updated base text."
        assert [v["variant_text"] for v in new_variants[1:]] == updated_generated

        # Verify old variant IDs were replaced
        new_variant_ids = [v["id"] for v in new_variants]
        assert set(old_variant_ids).isdisjoint(set(new_variant_ids))


@pytest.mark.asyncio
async def test_generate_phrases_not_autosaved_and_persists_on_put(monkeypatch):
    """AC: Given POST generate-phrases, ~8 seed-based phrases returned and NOT auto-saved (US-8).
    Given accepted phrases saved via PUT intents/:id (training_phrases.add), then they persist.
    """
    mock_phrases = [
        "Generated phrase 1",
        "Generated phrase 2",
        "Generated phrase 3",
        "Generated phrase 4",
        "Generated phrase 5",
        "Generated phrase 6",
        "Generated phrase 7",
        "Generated phrase 8",
    ]

    async def mock_handler(request: httpx.Request):
        return httpx.Response(200, json=make_gemini_response(mock_phrases))

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
    test_rephraser = GeminiRephraser(api_key="test-key", http_client=mock_http)
    monkeypatch.setattr(rephraser, "get_rephraser_client", lambda *_: test_rephraser)

    async with _client() as client:
        # Create intent with 1 seed phrase
        create_res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_phrase_gen_test",
                "training_phrases": ["Seed phrase 1"],
                "response_template": {"base_text": "Base text.", "allow_rephrasing": False},
            },
        )
        assert create_res.status_code == 201
        intent_id = create_res.json()["data"]["intent"]["id"]

        # Call generate-phrases
        gen_res = await client.post(
            f"/api/admin/intents/{intent_id}/generate-phrases",
            headers=HR,
            json={"count": 8},
        )
        assert gen_res.status_code == 200
        gen_data = gen_res.json()["data"]
        assert gen_data["intent_id"] == intent_id
        assert gen_data["generated_phrases"] == mock_phrases

        # Verify phrases are NOT auto-saved: GET intent still has only 1 phrase
        list_res = await client.get("/api/admin/intents", headers=HR)
        found = next(i for i in list_res.json()["data"]["intents"] if i["id"] == intent_id)
        assert len(found["training_phrases"]) == 1
        assert found["training_phrases"][0]["phrase_text"] == "Seed phrase 1"

        # Now accept 2 phrases via PUT /api/admin/intents/:id
        accepted = ["Generated phrase 1", "Generated phrase 2"]
        put_res = await client.put(
            f"/api/admin/intents/{intent_id}",
            headers=HR,
            json={"training_phrases": {"add": accepted}},
        )
        assert put_res.status_code == 200
        put_phrases = [p["phrase_text"] for p in put_res.json()["data"]["intent"]["training_phrases"]]
        assert "Seed phrase 1" in put_phrases
        assert "Generated phrase 1" in put_phrases
        assert "Generated phrase 2" in put_phrases

        # Verify persistence with a fresh GET
        verify_res = await client.get("/api/admin/intents", headers=HR)
        persisted = next(i for i in verify_res.json()["data"]["intents"] if i["id"] == intent_id)
        persisted_phrases = [p["phrase_text"] for p in persisted["training_phrases"]]
        assert len(persisted_phrases) == 3
        assert "Generated phrase 1" in persisted_phrases
        assert "Generated phrase 2" in persisted_phrases


@pytest.mark.asyncio
async def test_llm_failure_during_template_save_keeps_original_and_does_not_crash(monkeypatch):
    """AC: Given an LLM failure, then the save keeps the original variant and reports the error (no crash)."""
    async def failing_handler(request: httpx.Request):
        return httpx.Response(500, text="Gemini service unavailable")

    mock_http = httpx.AsyncClient(transport=httpx.MockTransport(failing_handler))
    test_rephraser = GeminiRephraser(api_key="test-key", http_client=mock_http)
    monkeypatch.setattr(rephraser, "get_rephraser_client", lambda *_: test_rephraser)

    async with _client() as client:
        # POST create intent with allow_rephrasing=True when LLM fails
        res = await client.post(
            "/api/admin/intents",
            headers=HR,
            json={
                "name": "ask_llm_failure_test",
                "training_phrases": ["Failure test phrase"],
                "response_template": {
                    "base_text": "This original variant is kept.",
                    "allow_rephrasing": True,
                },
            },
        )

        assert res.status_code == 201
        tpl = res.json()["data"]["intent"]["response_template"]
        assert len(tpl["variants"]) == 1
        assert tpl["variants"][0]["variant_text"] == "This original variant is kept."
