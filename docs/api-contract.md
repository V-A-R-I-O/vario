# API Contract — V.A.R.I.O (Voice Adaptive Role & Intent Orchestrator)

All endpoints are prefixed with `/api`. All responses use a standard envelope:

```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": "Error message string" | null
}
```

Authentication is delegated to the organization's identity provider via an Auth Adapter. VARIO issues its own JWT after the org validates the user. Protected routes require an `Authorization: Bearer <jwt>` header. The JWT payload contains `{ user_id, role, email }`.

---

## Auth

### `POST /api/auth/login`

Authenticate a user via the organization's identity provider. VARIO forwards credentials to the org's Auth Adapter (Mock Auth Service in dev/demo), and issues a VARIO JWT on success.

**Auth:** None

**Request:**
```json
{
  "email": "john.doe@example.com",
  "password": "password123"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "john.doe@example.com",
    "full_name": "John Doe",
    "role": "end_user | hr_admin | it_admin | admissions_admin",
    "external_id": "EMP-1001",
    "token": "jwt-string"
  },
  "error": null
}
```

**Side effects:**
- Upserts a record in the `users` table (creates on first login, updates on subsequent)
- Issues a JWT with `{user_id, role, email}` claims

**Errors:**
- `401` — Invalid credentials (org's auth rejected the login)

---

## Conversations

### `GET /api/conversations`

List all conversations for the authenticated user, ordered by most recent.

**Auth:** Any authenticated user

**Query params:**
- `role_pack` (optional) — filter by role pack (`hr`, `it`, `admissions`)
- `status` (optional) — filter by status (`active`, `archived`)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "conversations": [
      {
        "id": "uuid",
        "role_pack": "hr",
        "title": "Leave balance inquiry",
        "last_message_preview": "You have 12 days of leave remaining.",
        "status": "active",
        "created_at": "2026-09-07T10:00:00Z",
        "last_message_at": "2026-09-07T10:05:00Z"
      }
    ]
  },
  "error": null
}
```

---

### `POST /api/conversations`

Start a new conversation with a selected role pack. In the UI this is triggered by clicking a role-pack card (see `docs/ui-reference.md` page 3), which sends only `role_pack`.

**Auth:** Any authenticated user

**Request:**
```json
{
  "role_pack": "hr | it | admissions",
  "title": "Leave balance inquiry"
}
```

`title` is **optional**. If omitted, the server auto-generates a placeholder (e.g. `"New HR conversation"`) and replaces it with a title derived from the first user message once the conversation has content.

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "id": "uuid",
    "role_pack": "hr",
    "title": "Leave balance inquiry",
    "status": "active",
    "created_at": "2026-09-07T10:00:00Z"
  },
  "error": null
}
```

**Errors:**
- `422` — Invalid role_pack value

---

### `GET /api/conversations/:id/messages`

Fetch message history for a conversation.

**Auth:** Owner of the conversation

**Query params:**
- `limit` (optional, default 50) — number of messages to return
- `before` (optional) — cursor-based pagination, return messages before this message ID

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "conversation_id": "uuid",
    "messages": [
      {
        "id": "uuid",
        "sender": "user",
        "content": "What's my leave balance?",
        "intent_name": null,
        "confidence": null,
        "entities": null,
        "created_at": "2026-09-07T10:00:01Z"
      },
      {
        "id": "uuid",
        "sender": "bot",
        "content": "You have 12 days of leave remaining.",
        "intent_name": "check_leave_balance",
        "confidence": 0.95,
        "entities": { "employee_id": "EMP-1042" },
        "created_at": "2026-09-07T10:00:03Z"
      }
    ]
  },
  "error": null
}
```

**Errors:**
- `403` — Conversation does not belong to this user
- `404` — Conversation not found

---

## Chat

### `POST /api/chat`

Send a message in an existing conversation. This is the main endpoint — it routes through Session Manager → Dialogue Router → Rasa → Integration Adapter → Response Renderer, and optionally through TTS Service.

**Auth:** Owner of the conversation

**Request:**
```json
{
  "conversation_id": "uuid",
  "message": "What's my leave balance?",
  "mode": "chat | talk"
}
```

**Response (chat mode):** `200 OK`
```json
{
  "status": "success",
  "data": {
    "response_text": "You have 12 days of leave remaining.",
    "intent": "check_leave_balance",
    "confidence": 0.95,
    "entities": { "employee_id": "EMP-1042" },
    "session": {
      "current_form": null,
      "current_step": null,
      "slots": {}
    }
  },
  "error": null
}
```

**Response (talk mode):** `200 OK`
```json
{
  "status": "success",
  "data": {
    "response_text": "You have 12 days of leave remaining.",
    "audio_base64": "base64-encoded-audio-bytes",
    "audio_content_type": "audio/mp3",
    "intent": "check_leave_balance",
    "confidence": 0.95,
    "entities": { "employee_id": "EMP-1042" },
    "session": {
      "current_form": null,
      "current_step": null,
      "slots": {}
    },
    "tts_available": true
  },
  "error": null
}
```

When TTS credits are exhausted, `tts_available` is `false` and `audio_base64` is `null`. The frontend should fall back to chat-only and display "Talk mode not available, try again later."

**Errors:**
- `403` — Conversation does not belong to this user
- `404` — Conversation not found
- `422` — Missing conversation_id or message

---


## Admin — Intents

### `GET /api/admin/intents`

List all intents for the admin's role pack. Includes training phrases, response template, and variants for each intent.

**Auth:** Admin only (scoped to own role pack)

**Query params:**
- `needs_retrain` (optional, boolean) — filter by retrain status

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "role_pack": "hr",
    "intents": [
      {
        "id": "uuid",
        "name": "check_leave_balance",
        "intent_type": "dynamic_workflow",
        "needs_retrain": false,
        "updated_at": "2026-09-07T10:00:00Z",
        "training_phrases": [
          {
            "id": "uuid",
            "phrase_text": "What's my leave balance?",
            "created_at": "2026-09-07T10:00:00Z"
          },
          {
            "id": "uuid",
            "phrase_text": "How many leaves do I have?",
            "created_at": "2026-09-07T10:00:00Z"
          }
        ],
        "response_template": {
          "id": "uuid",
          "template_key": "check_leave_balance_response",
          "base_text": "You have {balance} days of leave remaining.",
          "allow_rephrasing": true,
          "available_variables": ["balance"],
          "variants": [
            {
              "id": "uuid",
              "variant_text": "Your current leave balance is {balance} days.",
              "generated_at": "2026-09-07T10:00:05Z"
            }
          ]
        }
      }
    ]
  },
  "error": null
}
```

---

### `POST /api/admin/intents`

Create a new intent with training phrases, a response template, and auto-generated variants. **Note:** Intents created via this endpoint are always created as `intent_type: "static_faq"` with an empty `available_variables` array, because Admins cannot create dynamic workflows from the UI (those are pre-seeded by developers). This is a synchronous call — the response includes the generated variants (~3–5 seconds due to Gemini API round-trip).

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "name": "ask_wfh_policy",
  "training_phrases": [
    "What is the WFH policy?",
    "Can I work from home?",
    "How many remote days do we get?",
    "Tell me about working from home"
  ],
  "response_template": {
    "base_text": "Employees are allowed to work from home up to 3 days per week.",
    "allow_rephrasing": true
  }
}
```

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "intent": {
      "id": "uuid",
      "name": "ask_wfh_policy",
      "role_pack": "hr",
      "intent_type": "static_faq",
      "needs_retrain": true,
      "training_phrases": [
        { "id": "uuid", "phrase_text": "What is the WFH policy?" },
        { "id": "uuid", "phrase_text": "Can I work from home?" },
        { "id": "uuid", "phrase_text": "How many remote days do we get?" },
        { "id": "uuid", "phrase_text": "Tell me about working from home" }
      ],
      "response_template": {
        "id": "uuid",
        "template_key": "ask_wfh_policy_response",
        "base_text": "Employees are allowed to work from home up to 3 days per week.",
        "allow_rephrasing": true,
        "available_variables": [],
        "variants": [
          { "id": "uuid", "variant_text": "Employees are allowed to work from home up to 3 days per week." },
          { "id": "uuid", "variant_text": "You can work remotely for a maximum of 3 days a week." },
          { "id": "uuid", "variant_text": "Our policy permits up to 3 work-from-home days weekly." },
          { "id": "uuid", "variant_text": "Staff may choose to work from home 3 days each week." },
          { "id": "uuid", "variant_text": "You're eligible for up to 3 days of remote work per week." }
        ]
      }
    }
  },
  "error": null
}
```

The first variant is always the original `base_text`. The remaining 4 are generated by the Gemini API. (So each template has **5** `response_variants` rows: the original at index 0 plus 4 generated.)

**`template_key` convention:** auto-generated by the server as `<intent_name>_response` (e.g. intent `ask_wfh_policy` → `ask_wfh_policy_response`). Admins never set it directly; the UI shows it as a read-only System Key.

**Errors:**
- `403` — Not an admin
- `409` — Intent name already exists for this role pack
- `422` — Validation error (missing name, empty training phrases, etc.)

---

### `PUT /api/admin/intents/:id`

Update an existing intent's name and/or training phrases. Sets `needs_retrain = true`.

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "name": "check_leave_balance",
  "training_phrases": {
    "add": [
      "Tell me my leave count"
    ],
    "remove": [
      "uuid-of-phrase-to-remove"
    ]
  }
}
```

All fields are optional — send only what you want to change.

**Note:** For a `dynamic_workflow` intent (pre-seeded by developers), the `name` is immutable — attempting to rename it returns `403`. Only its training phrases may be edited here; its response text is edited via `PUT /api/admin/templates/:id`. Renaming is allowed only for `static_faq` intents.

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "intent": {
      "id": "uuid",
      "name": "check_leave_balance",
      "needs_retrain": true,
      "training_phrases": [
        { "id": "uuid", "phrase_text": "What's my leave balance?" },
        { "id": "uuid", "phrase_text": "How many leaves do I have?" },
        { "id": "uuid", "phrase_text": "Tell me my leave count" }
      ]
    }
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin, intent belongs to another role pack, or attempt to rename a `dynamic_workflow` intent
- `404` — Intent not found
- `409` — New name already exists for this role pack

---

### `DELETE /api/admin/intents/:id`

Delete an intent and all its associated training phrases, response template, and variants. Sets `needs_retrain = true` for the role pack. **Note:** Only intents with `intent_type: "static_faq"` can be deleted. Dynamic workflows are pre-seeded by developers and cannot be deleted via the API.

**Auth:** Admin only (scoped to own role pack)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "deleted_intent_id": "uuid",
    "needs_retrain": true
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin, intent belongs to another role pack, or intent is a `dynamic_workflow` and cannot be deleted.
- `404` — Intent not found

---

## Admin — Response Templates

### `GET /api/admin/templates`

List all response templates for the admin's role pack, with their variants.

**Auth:** Admin only (scoped to own role pack)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "role_pack": "hr",
    "templates": [
      {
        "id": "uuid",
        "template_key": "check_leave_balance_response",
        "base_text": "You have {balance} days of leave remaining.",
        "allow_rephrasing": true,
        "available_variables": ["balance"],
        "updated_at": "2026-09-07T10:00:00Z",
        "variants": [
          {
            "id": "uuid",
            "variant_text": "You have {balance} days of leave remaining.",
            "generated_at": "2026-09-07T10:00:05Z"
          },
          {
            "id": "uuid",
            "variant_text": "Your current leave balance is {balance} days.",
            "generated_at": "2026-09-07T10:00:05Z"
          }
        ]
      }
    ]
  },
  "error": null
}
```

---

### `PUT /api/admin/templates/:id`

Update a response template's base text. If `allow_rephrasing` is true, this will re-generate 4 new variants synchronously (~3–5 seconds). Old variants are replaced.

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "base_text": "You currently have {balance} days of leave available.",
  "allow_rephrasing": true
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "template": {
      "id": "uuid",
      "template_key": "check_leave_balance_response",
      "base_text": "You currently have {balance} days of leave available.",
      "allow_rephrasing": true,
      "variants": [
        { "id": "uuid", "variant_text": "You currently have {balance} days of leave available." },
        { "id": "uuid", "variant_text": "Your available leave is {balance} days at present." },
        { "id": "uuid", "variant_text": "As of now, you have {balance} leave days remaining." },
        { "id": "uuid", "variant_text": "There are {balance} days of leave in your account." },
        { "id": "uuid", "variant_text": "You've got {balance} days of leave still available." }
      ]
    }
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin, or template belongs to another role pack
- `404` — Template not found

---

## Admin — Response Variants

### `PUT /api/admin/variants/:id`

Edit the text of a specific response variant.

**Auth:** Admin only (scoped to own role pack via parent template)

**Request:**
```json
{
  "variant_text": "Your leave balance currently stands at {balance} days."
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "variant": {
      "id": "uuid",
      "variant_text": "Your leave balance currently stands at {balance} days.",
      "generated_at": "2026-09-07T10:00:05Z"
    }
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin, or variant's parent template belongs to another role pack
- `404` — Variant not found
- `422` — Placeholder validation failed (variant is missing placeholders present in the base template)

---

### `DELETE /api/admin/variants/:id`

Delete a specific response variant. The original base_text variant (first one) cannot be deleted.

**Auth:** Admin only (scoped to own role pack via parent template)

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "deleted_variant_id": "uuid"
  },
  "error": null
}
```

**Errors:**
- `400` — Cannot delete the original base_text variant
- `403` — Not an admin, or variant's parent template belongs to another role pack
- `404` — Variant not found

---

## Admin — Training Phrase Generation

### `POST /api/admin/intents/:id/generate-phrases`

Generate additional training phrase variants for an existing intent using the rephraser service. Uses the existing training phrases as seed input.

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "count": 8
}
```

`count` is optional (default: 8). Specifies how many phrase variants to generate.

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "intent_id": "uuid",
    "generated_phrases": [
      "How many leaves do I have left?",
      "Can you check my leave balance?",
      "Tell me my remaining leave days",
      "I want to know my leave balance",
      "How much leave do I have?",
      "Check my leaves remaining",
      "What is my current leave count?",
      "Show me how many leaves are left"
    ]
  },
  "error": null
}
```

Generated phrases are NOT automatically saved. The frontend presents them to the admin for review (accept/edit/reject). Accepted phrases are then saved via `PUT /api/admin/intents/:id` with the `training_phrases.add` array.

**Errors:**
- `403` — Not an admin, or intent belongs to another role pack
- `404` — Intent not found
- `422` — Intent has no existing training phrases to use as seed

---

## Admin — Retraining

### `POST /api/admin/retrain`

Trigger manual retraining for the admin's role pack. Reads all intents and training phrases from the DB, converts to Rasa YAML, trains, and reloads the model. This is a long-running operation (~30–120 seconds depending on training data size).

The role pack is **derived from the JWT role claim**, never from the request — an admin can only retrain their own pack. No request body is required (an empty `{}` is fine).

**Auth:** Admin only (scoped to own role pack)

**Request:** *(no body required)*
```json
{}
```

**Response:** `202 Accepted`
```json
{
  "status": "success",
  "data": {
    "retrain_job_id": "uuid",
    "role_pack": "hr",
    "message": "Retraining started. This may take 1–2 minutes."
  },
  "error": null
}
```

The frontend can poll for completion:

### `GET /api/admin/retrain/:job_id`

Check status of a retraining job.

**Auth:** Admin only

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "retrain_job_id": "uuid",
    "role_pack": "hr",
    "state": "pending | training | complete | failed",
    "started_at": "2026-09-07T10:00:00Z",
    "completed_at": "2026-09-07T10:01:30Z",
    "error_message": null
  },
  "error": null
}
```

---

## Admin — Conversation Logs

These endpoints back the **Conversation Logs** admin page (see `docs/ui-reference.md` page 10) and satisfy **FR-19** (a Role Admin can view conversations handled by their role pack's bot). They are distinct from the end-user `GET /api/conversations` routes, which are scoped to the *caller's own* conversations. Here the scope is **every conversation in the admin's role pack**, read-only.

### `GET /api/admin/conversations`

List conversations handled by the admin's role pack, most recent first.

**Auth:** Admin only (scoped to own role pack via JWT — the `role_pack` is derived from the token, never from the caller)

**Query params:**
- `actor_id` (optional) — filter by the end user who held the conversation
- `from` / `to` (optional) — ISO 8601 date range on `started_at`
- `limit` (optional, default 50) — number of entries
- `offset` (optional, default 0) — pagination offset

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "role_pack": "hr",
    "total": 87,
    "conversations": [
      {
        "id": "uuid",
        "user_name": "John Doe",
        "user_email": "john.doe@example.com",
        "title": "Leave balance inquiry",
        "message_count": 6,
        "last_intent": "check_leave_balance",
        "started_at": "2026-09-07T10:00:00Z",
        "last_message_at": "2026-09-07T10:05:00Z"
      }
    ]
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin

---

### `GET /api/admin/conversations/:id/messages`

Fetch the full, read-only transcript of one conversation in the admin's role pack. Each bot message carries the detected intent and confidence (for the "where did the bot misunderstand?" review flow).

**Auth:** Admin only. The conversation must belong to the admin's role pack — an HR admin cannot read an IT conversation.

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "conversation_id": "uuid",
    "role_pack": "hr",
    "user_name": "John Doe",
    "messages": [
      {
        "id": "uuid",
        "sender": "user",
        "content": "What's my leave balance?",
        "intent_name": null,
        "confidence": null,
        "entities": null,
        "created_at": "2026-09-07T10:00:01Z"
      },
      {
        "id": "uuid",
        "sender": "bot",
        "content": "You have 12 days of leave remaining.",
        "intent_name": "check_leave_balance",
        "confidence": 0.95,
        "entities": { "employee_id": "EMP-1042" },
        "created_at": "2026-09-07T10:00:03Z"
      }
    ]
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin, or the conversation belongs to another role pack
- `404` — Conversation not found

---

## Admin — Audit Log

### `GET /api/admin/audit-log`

View audit log entries for the admin's role pack.

**Auth:** Admin only (scoped to own role pack)

**Query params:**
- `action_type` (optional) — filter by action type (e.g., `leave_submitted`, `ticket_created`, `intent_updated`, `template_edited`)
- `actor_id` (optional) — filter by actor
- `from` (optional) — ISO 8601 start date
- `to` (optional) — ISO 8601 end date
- `limit` (optional, default 50) — number of entries
- `offset` (optional, default 0) — pagination offset

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "role_pack": "hr",
    "total": 142,
    "entries": [
      {
        "id": "uuid",
        "actor_id": "uuid",
        "actor_name": "John Doe",
        "action_type": "leave_submitted",
        "reference_id": "LEAVE-2031",
        "details": {
          "leave_type": "casual",
          "days": 2,
          "from": "2026-09-10",
          "to": "2026-09-11"
        },
        "created_at": "2026-09-07T10:05:00Z"
      }
    ]
  },
  "error": null
}
```

---

## Error Response Format

All errors follow the same envelope:

```json
{
  "status": "error",
  "data": null,
  "error": "Human-readable error message"
}
```

### Standard HTTP Status Codes

| Code | Meaning |
|---|---|
| `200` | Success |
| `201` | Created |
| `202` | Accepted (async job started) |
| `400` | Bad request (business rule violation) |
| `401` | Unauthorized (missing or invalid JWT) |
| `403` | Forbidden (valid JWT but insufficient permissions) |
| `404` | Resource not found |
| `409` | Conflict (duplicate resource) |
| `422` | Validation error (malformed request body) |
| `429` | Rate limited |
| `500` | Internal server error |

---

## Rate Limiting

Rate limits are applied at the API Gateway level per authenticated user:

| Endpoint Group | Limit |
|---|---|
| `/api/auth/*` | 10 requests/minute (per IP) |
| `/api/chat` | 30 requests/minute (per user) |
| `/api/conversations/*` | 60 requests/minute (per user) |
| `/api/admin/*` | 30 requests/minute (per user) |
| `/api/admin/retrain` | 3 requests/hour (per user) |

When rate limited, the response includes:
```json
{
  "status": "error",
  "data": null,
  "error": "Rate limit exceeded. Try again in 45 seconds."
}
```

Headers included: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
