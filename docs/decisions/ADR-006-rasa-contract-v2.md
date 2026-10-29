# ADR 006: Rasa Converse Contract v2

**Date:** 2026-10-29
**Status:** Accepted
**Slice:** slice-32-rasa-contract-v2 (SCRUM-42)
**Supersedes:** the request/response shape in ADR-002. ADR-002's endpoint path and `CONFIDENCE_THRESHOLD` still apply.

## Context

EPIC-5 moves the three role packs to real Rasa Open Source 3.6.20 (slices 35, 37 and 39). ADR-002 assumed the gateway owns all dialogue state and replays it every turn. Real Rasa keeps that state in its own tracker, keyed by the sender.

The Sprint 3 integration audit (`docs/testing/sprint-3-integration-audit.md`) also traced several defects to the old contract:

| Defect | Cause in the old contract |
|---|---|
| **B5a/B5b** | The gateway merged slots forever, and the UI picked cards from that pile. |
| **M12** | Cards weren't stored per message, so they vanished on reload. |
| **B6/M2** | The trusted identity was optional, and packs ignored it. |
| **M6** | A role-pack outage became a 500 with no CORS header, and the user's message was lost. |
| — | Security-answer redaction was hard-coded to IT's form and step names. |

The UI and all three packs must build against one frozen contract in parallel. This ADR is that contract.

## Decision

### 1. Endpoint (unchanged)

```
POST {RASA_<PACK>_URL}/webhooks/vario/converse
```

Every Rasa server serves this through the shared custom input channel `vario_rasa.channel.VarioInputChannel` (§7).

### 2. Request — gateway → role pack

```json
{
  "sender": "<conversation_id>",
  "message": "What's my leave balance?",
  "metadata": {
    "auth_context": { "employee_id": "EMP-1001", "full_name": "Employee One", "role": "end_user" },
    "user_id": "<VARIO users.user_id>",
    "sensitive": false
  },
  "session": { "current_form": null, "current_step": null, "slots": {} },
  "auth_context": { "employee_id": "EMP-1001", "full_name": "Employee One", "role": "end_user" }
}
```

| Field | Rule |
|---|---|
| `sender` | The **conversation ID**, so each conversation gets its own Rasa tracker. ADR-002 used the user ID, which would make all of a user's conversations with one pack share a single tracker. |
| `metadata.auth_context` | The trusted identity, from the authenticated user (`users.external_id`). For "my …" questions, the employee ID comes **only** from here, never from chat text. Actions read it as `tracker.latest_message["metadata"]["auth_context"]`. |
| `metadata.user_id` | VARIO's internal user ID, for logging/audit only. |
| `metadata.sensitive` | `true` when the previous reply set `sensitive_next_input`: this message is a secret (§6). |
| `session` | The gateway's mirror (§5). Only the pre-Rasa (v1) packs read it; Rasa packs ignore it. |
| top-level `auth_context` | **Deprecated** copy for the v1 IT pack. Removed after slice-37. |

### 3. Response — role pack → gateway

```json
{
  "intent": "check_leave_balance",
  "confidence": 0.96,
  "entities": {},
  "template_key": "check_leave_balance_response",
  "slots": { "total": 22, "casual": 4, "sick": 6, "earned": 12 },
  "current_form": null,
  "current_step": null,
  "response_text": "You have 22 days of leave remaining: 4 casual, 6 sick, 12 earned.",
  "audit_event": null,
  "card": {
    "type": "data_card",
    "title": "Your leave balance",
    "rows": [{ "label": "Casual", "value": "4 days" }, { "label": "Total", "value": "22 days" }]
  },
  "sensitive_next_input": false
}
```

| Field | Rule |
|---|---|
| `intent`, `confidence`, `entities` | The NLU parse of *this* message (`tracker.latest_message`). Entities are returned as `{entity: value}`; if an entity appears twice, the last value wins. |
| `template_key`, `slots` | Optional. `slots` holds **only the values this turn's template needs**, not the dialogue state. The gateway renders a stored, admin-editable variant when one exists; otherwise it uses `response_text`. |
| `current_form`, `current_step` | Rasa's `active_loop` and `requested_slot` after the turn. Both are `null` when no form is active. |
| `response_text` | The turn's bot text messages, joined with a blank line. |
| `audit_event` | `{action_type, reference_id, details}` or `null`. The gateway writes it to `audit_log`. |
| `card` | One UI card for this turn, or `null`. Its shape is **exactly the frontend `BotMessageData`** from `frontend/src/components/chat/types.ts` (ui-reference §4), minus the callbacks. Allowed types: `plain_text`, `data_card`, `slot_prompt`, `confirmation`, `result`, `not_found`, `faq_answer`, `error`, `list`. The canonical list is `rasa-shared/contract/card-types.json`. A card with any other type is dropped by both the channel and the gateway. |
| `sensitive_next_input` | `true` when this reply asks for a secret (§6). |

Packs compose the generic UI types (e.g. a leave balance is a `data_card`), so a new role pack needs no frontend code (FR-3).

**How a Rasa pack produces these fields.** Actions — or domain responses, via `custom:` — emit the VARIO fields as custom JSON under the `vario` key:

```python
from vario_rasa.contract import vario_payload

dispatcher.utter_message(text="You have 22 days left.")
dispatcher.utter_message(json_message=vario_payload(
    template_key="check_leave_balance_response",
    slots={"total": 22, "casual": 4, "sick": 6, "earned": 12},
    card={"type": "data_card", "title": "Your leave balance", "rows": [...]},
))
```

The channel then assembles the response from the turn's collected messages:
- Text parts become `response_text`.
- The last `vario` payload supplies `template_key`, `slots`, `card`, `audit_event` and `sensitive_next_input`.
- A text message with Rasa `buttons` becomes a `slot_prompt` card when no explicit card was sent. Each button's `title` becomes an option label and its `payload` the option value, so the UI sends the payload back (e.g. `/inform{"leave_type":"sick"}`).

### 4. Gateway behaviour

| Situation | Behaviour |
|---|---|
| Normal turn | Render the variant or `response_text`. Persist the bot message with intent, confidence, entities and **card**. Store the session mirror **exactly as returned** — no merge. |
| `confidence < CONFIDENCE_THRESHOLD`, no form active before the turn | Return the clarification prompt; the session is unchanged (FR-2). |
| Low confidence **while a form is active** | Use the pack's reply as-is. A free-text slot answer such as "fever" must not trigger "please rephrase". |
| Pack unreachable, timeout, 4xx/5xx or invalid JSON | Return HTTP 200 with `degraded: true` and the text "The *HR/IT support/Admissions* assistant is unavailable right now. Please try again in a moment." The card is `{"type":"error","text":…}`. Both messages are stored and the session is unchanged. |
| Previous reply had `sensitive_next_input` | Store the user message as `[security answer redacted]` and send it with `metadata.sensitive: true`. The flag is cleared after the turn. The legacy rule (v1 IT form/step names) stays until slice-37. |
| Session expired (`expires_at` passed) | Clear form, step and slots before routing. Rasa packs set `session_config.session_expiration_time` to `SESSION_TTL_MINUTES` so both sides expire together. |
| Unhandled server error | HTTP 500 envelope **with CORS headers**. The gateway middleware answers inside the CORS layer. |

`POST /api/chat` adds `card` and `degraded` to its response, and message history adds `card` to each message (see `docs/api-contract.md`).

#### Example — form turn (`/api/chat` data)

```json
{
  "response_text": "What type of leave would you like to request?",
  "intent": "submit_leave_request", "confidence": 0.91, "entities": {},
  "session": { "current_form": "leave_request_form", "current_step": "leave_type", "slots": {} },
  "card": { "type": "slot_prompt", "text": "What type of leave would you like to request?",
            "options": [{ "label": "Casual", "value": "casual" }, { "label": "Sick", "value": "sick" }] },
  "degraded": false
}
```

#### Example — degraded turn (`/api/chat` data)

```json
{
  "response_text": "The HR assistant is unavailable right now. Please try again in a moment.",
  "intent": null, "confidence": null, "entities": {},
  "session": { "current_form": "leave_request_form", "current_step": "leave_type", "slots": {} },
  "card": { "type": "error", "text": "The HR assistant is unavailable right now. Please try again in a moment." },
  "degraded": true
}
```

### 5. Where dialogue state lives

- **Rasa packs:** Rasa's SQL tracker store, in the stack's Postgres, with one database per pack (`rasa_hr`, `rasa_it`, `rasa_admissions`). Slice-34 creates these databases. Trackers survive restarts (NFR reliability). This tracker is the source of truth.
- **Gateway `sessions` row:** a mirror of what the pack last reported, used for the UI, logs and the v1 packs. Since every pack returns its own state, the mirror is replaced each turn, never merged.

### 6. Secrets at rest

Rasa stores every user message (text, parse data and any slot filled from it) in its tracker store. Packs must use `vario_rasa.tracker_store.RedactingSQLTrackerStore`. When a user turn arrives with `metadata.sensitive: true`:
- it is saved as `[redacted]`, with no entities;
- any slot set to that text in the same turn is saved as `[redacted]` too.

Actions still see the real text during the turn, so a `validate_<slot>` method can verify the answer. Actions must not keep a secret in a slot afterwards. No Rasa event broker is configured, so nothing else receives the raw text.

### 7. Shared module and fixtures

`rasa-shared/` holds the only copy:

| Path | What it is |
|---|---|
| `vario_rasa/contract.py` | Pure Python, no Rasa import: `vario_payload()`, `build_converse_response()`, `CARD_TYPES`. Action servers may import it. |
| `vario_rasa/channel.py` | `VarioInputChannel`. |
| `vario_rasa/tracker_store.py` | `RedactingSQLTrackerStore`. |
| `contract/*.json` | Frozen request/response examples. The gateway tests, the channel tests and the pack/UI slices all test against them. |

How packs get the module:
- **Docker:** Rasa containers mount `rasa-shared/vario_rasa` read-only at `/app/vario_rasa` (slice-34).
- **Native:** set `PYTHONPATH=<repo>/rasa-shared`.

Packs register it in their config files:

```yaml
# credentials.yml
vario_rasa.channel.VarioInputChannel: {}

# endpoints.yml
tracker_store:
  type: vario_rasa.tracker_store.RedactingSQLTrackerStore
  dialect: postgresql
  url: postgres
  db: rasa_hr
  username: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}
```

### 8. Transition

Until slices 35, 37 and 39 replace the v1 packs, the gateway keeps sending `session` and the top-level `auth_context`. The v1 packs already return their full state in `slots`, so storing the mirror without merging preserves their behaviour. This was verified end-to-end against the current HR, IT and Admissions packs. Remove both deprecated fields, and the legacy IT redaction rule, after slice-37.

## Consequences

- **Positive:**
  - Packs and UI build in parallel against frozen fixtures.
  - Stale-slot bugs lose their root cause.
  - Cards survive reloads.
  - Identity has one trusted path.
  - Outages degrade instead of crashing.
  - Secrets stay out of both databases.
- **Positive:** Cards reuse the UI's generic message types, so role packs stay configuration plus actions, with no frontend code (FR-3).
- **Negative:** Packs must emit the `vario` payload deliberately; plain Rasa responses give only `response_text`, plus a `slot_prompt` card when they have buttons.
- **Negative:** One schema migration (`messages.card`, `sessions.sensitive_next_input`), which needs human review.
- **Follow-ups:**
  - Slice-33 renders cards from `card`.
  - Slice-34 mounts `rasa-shared`, creates the `rasa_*` databases and wires `endpoints.yml`.
  - Slice-38 adds `rasa-shared` tests to CI.
