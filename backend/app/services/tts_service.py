"""tts-service — wraps Google Cloud Text-to-Speech (Neural2).

Only called for `mode: "talk"` (ADD §tts-service). Text in, audio bytes out.
Degrades gracefully: if credentials are unset, credits are exhausted, or the
API call fails, it returns `available=False` with no audio rather than raising,
so the chat turn still returns its text reply.

The single outbound call lives in `_synthesize_bytes`, an injectable seam that
tests patch (mirrors `dialogue_router._post_to_rasa`). The Google client library
is imported lazily inside that seam so the app runs — and tests patch — without
the dependency installed or credentials present.
"""
import base64
import logging
from dataclasses import dataclass
from typing import Optional

from starlette.concurrency import run_in_threadpool

from app.config import settings

logger = logging.getLogger("vario.tts_service")

# Google Cloud TTS returns MP3 bytes for this config (api-contract § talk mode).
AUDIO_CONTENT_TYPE = "audio/mp3"
_VOICE_LANGUAGE_CODE = "en-US"
_VOICE_NAME = "en-US-Neural2-C"


@dataclass
class TtsResult:
    """Outcome of a synthesis attempt. `available` is False on any degrade path."""

    available: bool
    audio_base64: Optional[str] = None
    audio_content_type: Optional[str] = None


def _synthesize_bytes(text: str) -> bytes:
    """Injectable seam: the single blocking Google Cloud TTS call. Tests patch this.

    Imported lazily so the module loads without `google-cloud-texttospeech`.
    """
    from google.cloud import texttospeech

    client = texttospeech.TextToSpeechClient()
    response = client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=_VOICE_LANGUAGE_CODE,
            name=_VOICE_NAME,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        ),
    )
    return response.audio_content


async def synthesize(text: str) -> TtsResult:
    """Synthesize `text` to audio. Never raises — returns a degrade flag instead."""
    if not settings.GOOGLE_APPLICATION_CREDENTIALS:
        logger.warning("TTS credentials not configured; talk mode degrading to text-only")
        return TtsResult(available=False)

    try:
        # The client is synchronous/blocking — keep it off the event loop.
        audio_bytes = await run_in_threadpool(_synthesize_bytes, text)
    except Exception:
        # Credits exhausted, auth failure, network error — all degrade to text.
        logger.exception("TTS synthesis failed; talk mode degrading to text-only")
        return TtsResult(available=False)

    if not audio_bytes:
        logger.warning("TTS returned empty audio; talk mode degrading to text-only")
        return TtsResult(available=False)

    return TtsResult(
        available=True,
        audio_base64=base64.b64encode(audio_bytes).decode("ascii"),
        audio_content_type=AUDIO_CONTENT_TYPE,
    )
