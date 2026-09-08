# Slice 06 — talk-mode

> One slice = one agent session (one sitting, one context window). It's fine if it produces 2–3 small commits/PRs, not just one — the boundary is coherence, not commit count. If the acceptance criteria below stop being checkable as a single unit, split it into two slices.

**Owner:** D · **Sprint:** 3 · **Module:** `tts-service` (+ Talk Mode UI, Web Speech STT)

## References — read these first
- `AGENTS.md` (human review required — this wires a credential/secret)
- `docs/api-contract.md` § Chat → **talk mode** response (`audio_base64`, `audio_content_type`, `tts_available`, degrade behaviour)
- `docs/ADD.md` → `tts-service` module + talk-mode flow diagram
- `docs/ui-reference.md` § 5 (Talk Mode overlay: mic states, auto-play, hands-free loop, unavailable banner)
- `docs/vario-overview.md` § 7 (Usability: voice + text, text fallback when no Web Speech API)
- `.env.example` (`GOOGLE_APPLICATION_CREDENTIALS`)

## What to build
Voice in/out layered on the existing chat pipeline. STT happens in the browser (Web Speech API); TTS happens server-side (Google Cloud Neural2). Talk mode is a toggle on the Chat View, not a separate page. Degrade gracefully at every step.

Deliverables:
- **tts-service** — wraps Google Cloud TTS (Neural2). Text → audio bytes. Called only for `mode: "talk"`. If credits are exhausted or the call fails, return a flag rather than throwing.
- **Extend `POST /api/chat` for `mode: "talk"`** — after rendering the text response, synthesize audio and return `response_text` + `audio_base64` + `audio_content_type` + `tts_available`. On TTS failure: `tts_available: false`, `audio_base64: null`, text still returned.
- **Talk Mode UI** (overlay on Chat View):
  - Microphone button with idle / listening (pulsing) / processing states.
  - Web Speech API STT → live transcript into the input bar → auto-send when the user stops.
  - Bot responses auto-play as audio; a speaker icon replays a bot message.
  - After audio finishes, STT auto-restarts (hands-free loop).
  - "Talk mode unavailable" banner + "Switch to text" action when `tts_available` is false.
  - If the browser lacks the Web Speech API, text input remains fully usable.

## Acceptance criteria
- [ ] Given a `mode: "talk"` chat request with TTS available, then the response includes `audio_base64`, `audio_content_type`, and `tts_available: true`.
- [ ] Given TTS credits exhausted or a TTS failure, then the response has `tts_available: false` and `audio_base64: null`, and the text reply is still returned (no crash).
- [ ] Given talk mode, when the user taps the mic and speaks, then the transcript appears in the input bar and the message auto-sends when they stop.
- [ ] Given a bot reply in talk mode, then its audio auto-plays, and the speaker icon replays it.
- [ ] Given audio playback finishes, then STT auto-restarts (hands-free loop continues).
- [ ] Given `tts_available: false`, then the "Talk mode unavailable" banner with "Switch to text" is shown.
- [ ] Given a browser without the Web Speech API, then text chat still works (graceful fallback).

## Mockup / reference (if UI-facing)
`docs/design/talk-mode.html` (matches `docs/ui-reference.md` §5).

## Out of scope for this slice
- Server-side STT (the browser does STT).
- Multi-language voices / voice-selection UI.
- Changing the chat-mode contract (`slice-05`) — this only adds the talk-mode fields.

## Human review required?
**Yes** — wires Google Cloud TTS credentials (a secret). Review the credential/env handling (per `AGENTS.md`).
