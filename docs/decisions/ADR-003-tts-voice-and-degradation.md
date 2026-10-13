# ADR 003: TTS Voice, Audio Encoding & Talk-Mode Degradation

**Date:** 2026-10-13
**Status:** Accepted
**Slice:** slice-06-talk-mode

## Context
`slice-06` adds voice to the existing chat pipeline. STT runs in the browser (Web Speech API); TTS runs server-side via Google Cloud Text-to-Speech (Neural2). `docs/ADD.md` and `docs/api-contract.md` fix the response shape (`audio_base64`, `audio_content_type`, `tts_available`) and require graceful degradation, but leave three things unspecified: which voice/encoding to synthesize, how to invoke a blocking client from an async request, and exactly when talk mode should degrade.

## Decision

### Voice & encoding
- Voice: **`en-US-Neural2-C`**, language `en-US`. English-only; multi-language/voice selection is explicitly out of scope for this slice.
- Encoding: **MP3** → `audio_content_type: "audio/mp3"`, matching the example in `docs/api-contract.md`. The frontend plays it via a `data:audio/mp3;base64,…` URI.

### Service shape
- `tts-service` exposes `async synthesize(text) -> TtsResult(available, audio_base64, audio_content_type)`. The single outbound Google call lives behind an injectable seam `_synthesize_bytes`, mirroring `dialogue_router._post_to_rasa`, so the chat engine is testable without the dependency or real credentials.
- The Google client is synchronous; it is run via `starlette.concurrency.run_in_threadpool` to keep it off the event loop.
- `google-cloud-texttospeech` is imported **lazily** inside the seam so the app boots (and tests run) without the library installed or `GOOGLE_APPLICATION_CREDENTIALS` set.

### Degradation (never raises)
`synthesize` returns `available=False` (and the endpoint sets `tts_available: false`, `audio_base64: null`) when:
1. `GOOGLE_APPLICATION_CREDENTIALS` is empty — the seam is never called.
2. The Google call raises (credits exhausted, auth/network failure).
3. The call returns empty audio.

In every case the rendered **text reply is still returned** — talk mode degrades to chat, it never fails the turn. On the client, `tts_available: false` surfaces the "Talk mode is temporarily unavailable" banner with a "Switch to text" action, and a browser lacking the Web Speech API keeps full text input.

## Consequences
- **Positive:** Talk mode is additive — the chat-mode contract (slice-05) is unchanged; talk fields are null in chat mode.
- **Positive:** The TTS boundary is mocked in tests exactly like the Rasa boundary, so the endpoint and service are fully unit-tested without credentials.
- **Negative:** Credentials wiring (`GOOGLE_APPLICATION_CREDENTIALS`) is a secret and requires human review before deploy (per `AGENTS.md`). The variable already exists in `.env.example`; no secret value is committed.
- **Tunable:** Voice/encoding are constants in `tts_service.py`; changing them (or adding voice selection) is a later concern, deliberately deferred.
