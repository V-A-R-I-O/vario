# ADR 002: Rasa Chat Contract & Confidence Threshold

**Date:** 2026-10-10
**Status:** Accepted
**Slice:** slice-05-chat-core

## Context
`slice-05` builds the conversation engine (`session-manager` + `dialogue-router` + `response-renderer`) and the `POST /api/chat` endpoint. The dialogue router must forward a message to the correct role-pack Rasa instance and hand the result to the renderer. Two things were under-specified and had to be pinned down so the chat engine could be built and tested before the Rasa instances exist (those land in slices 12/17/22):

1. **What the router sends to Rasa and what shape it gets back.** `docs/ADD.md` only says Rasa returns "Intent + template key + slots". The stock Rasa REST channel (`/webhooks/rest/webhook`) and NLU endpoint (`/model/parse`) don't return a single payload carrying intent + confidence + entities + template_key + slots + form state together.
2. **The confidence threshold** below which a low-confidence top intent becomes a clarification prompt instead of a workflow (FR-2). No numeric value was given anywhere in the docs.

## Decision

### Rasa converse contract
Each role-pack Rasa instance exposes a VARIO-specific endpoint:

```
POST {RASA_*_URL}/webhooks/vario/converse
```

**Request** (sent by `dialogue-router`):
```json
{
  "sender": "<user_id>",
  "message": "<user text>",
  "session": { "current_form": null, "current_step": null, "slots": {} }
}
```

**Response** (consumed by the chat engine):
```json
{
  "intent": "check_leave_balance",
  "confidence": 0.95,
  "entities": { "employee_id": "EMP-1042" },
  "template_key": "check_leave_balance_response",
  "slots": { "balance": 12 },
  "current_form": null,
  "current_step": null,
  "response_text": null
}
```

- `template_key` + `slots` drive the `response-renderer` (random stored variant + placeholder substitution). `response_text` is an optional direct-text escape hatch used only when a template has no stored variants.
- The router is a pure dispatcher: it resolves `role_pack → RASA_*_URL` (`hr`→`RASA_HR_URL`, `it`→`RASA_IT_URL`, `admissions`→`RASA_ADMISSIONS_URL`), makes the one outbound call, and parses the payload. The single HTTP call lives behind an injectable seam (`_post_to_rasa`) so the engine is testable without a live Rasa.
- The role-pack slices (12/17/22) are responsible for implementing this endpoint inside their Rasa custom actions (where the integration-adapter calls happen).

### Confidence threshold
`CONFIDENCE_THRESHOLD` is configurable (env/`config.py`), defaulting to **0.4**. When `confidence < CONFIDENCE_THRESHOLD`, the engine returns a fixed clarification prompt and does **not** render a workflow response or advance the session's form/step (FR-2). The session TTL is still refreshed.

## Consequences
- **Positive:** The chat engine, renderer, and session manager are fully built and unit-tested now, with the Rasa boundary mocked. Role-pack slices have an explicit contract to implement rather than inventing one each.
- **Positive:** Keeping the router a pure dispatcher (no NLU, no threshold logic) matches the ADD module boundaries; the threshold/clarification decision lives in the chat orchestration layer.
- **Negative:** The role-pack Rasa slices must add a custom channel/action to emit this payload — it is not Rasa's out-of-the-box REST shape. This is documented here so those slices don't rediscover it.
- **Tunable:** `0.4` is a starting point for demo data; adjust per-pack once real training data exists. It is config, not a constant, precisely so it can change without code edits.
