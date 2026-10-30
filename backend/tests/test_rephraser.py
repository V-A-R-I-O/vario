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

