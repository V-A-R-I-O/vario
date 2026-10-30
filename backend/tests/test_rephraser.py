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
