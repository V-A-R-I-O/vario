"""Unit tests for the tts-service (slice-06).

The Google client call (`_synthesize_bytes`) is patched, so these run without
the `google-cloud-texttospeech` dependency or real credentials.
"""
import base64

import pytest
from unittest.mock import patch

from app.config import settings
from app.services import tts_service


@pytest.mark.asyncio
async def test_synthesize_returns_audio_when_available():
    """Credentials present + a successful call → available with base64 audio."""
    with patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", "/fake/sa.json"), patch(
        "app.services.tts_service._synthesize_bytes", return_value=b"RAW-AUDIO-BYTES"
    ):
        result = await tts_service.synthesize("You have 12 days of leave remaining.")

    assert result.available is True
    assert result.audio_content_type == "audio/mp3"
    assert base64.b64decode(result.audio_base64) == b"RAW-AUDIO-BYTES"


@pytest.mark.asyncio
async def test_synthesize_degrades_when_credentials_missing():
    """No credentials → available=False, no audio, and the seam is never called."""
    with patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", ""), patch(
        "app.services.tts_service._synthesize_bytes"
    ) as seam:
        result = await tts_service.synthesize("hello")

    assert result.available is False
    assert result.audio_base64 is None
    assert result.audio_content_type is None
    seam.assert_not_called()


@pytest.mark.asyncio
async def test_synthesize_degrades_on_api_failure():
    """A failing/credit-exhausted API call degrades instead of raising."""
    with patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", "/fake/sa.json"), patch(
        "app.services.tts_service._synthesize_bytes",
        side_effect=RuntimeError("quota exceeded"),
    ):
        result = await tts_service.synthesize("hello")

    assert result.available is False
    assert result.audio_base64 is None
