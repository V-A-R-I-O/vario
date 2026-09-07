# API Contract — V.A.R.I.O (Voice Adaptive Role & Intent Orchestrator)

All endpoints are prefixed with `/api`. All responses use a standard envelope:

```json
{
  "status": "success" | "error",
  "data": { ... },
  "error": "Error message string" | null
}
```

Authentication is via `Authorization: Bearer <jwt>` header on all protected routes. The JWT payload contains `{ user_id, role, email }`.

---

## Auth

### `POST /api/auth/register`

Register a new end user. Always assigns `end_user` role — there is no way to self-register as an admin. Account is created with `email_verified = false`. A verification email is sent via Gmail SMTP. The user **cannot log in until verified**.

**Auth:** None

**Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword",
  "full_name": "John Doe",
  "external_id": "EMP-1042"
}
```

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "end_user",
    "email_verified": false,
    "message": "Registration successful. Please check your email to verify your account."
  },
  "error": null
}
```

**Side effects:**
- Creates an `auth_tokens` entry with `type: "email_verification"` and 24-hour expiry
- Sends a verification email with a link: `https://<frontend-url>/verify-email?token=<raw-token>`

**Errors:**
- `409` — Email already registered
- `422` — Validation error (missing/invalid fields)

---

### `POST /api/auth/verify-email`

Verify a user's email address using the token from the verification link.

**Auth:** None

**Request:**
```json
{
  "token": "raw-token-from-email-link"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Email verified successfully. You can now log in."
  },
  "error": null
}
```

**Side effects:**
- Sets `email_verified = true` on the user
- Marks the token as `used = true`

**Errors:**
- `400` — Token is invalid, expired, or already used

---

### `POST /api/auth/resend-verification`

Resend the verification email. Invalidates any previous verification tokens for this user.

**Auth:** None

**Request:**
```json
{
  "email": "john@example.com"
}
```

**Response:** `200 OK` (always, even if email not found — prevents enumeration)
```json
{
  "status": "success",
  "data": {
    "message": "If an unverified account with that email exists, a new verification link has been sent."
  },
  "error": null
}
```

**Side effects:**
- Invalidates previous verification tokens for this user
- Creates a new `auth_tokens` entry with `type: "email_verification"` and 24-hour expiry
- Sends a new verification email
- Does nothing if the email doesn't exist or is already verified

---

### `POST /api/auth/login`

Login for both end users and admins.

**Auth:** None

**Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "john@example.com",
    "full_name": "John Doe",
    "role": "end_user | hr_admin | it_admin | admissions_admin",
    "token": "jwt-string"
  },
  "error": null
}
```

**Errors:**
- `401` — Invalid email or password
- `403` — Email not verified. Response includes a message prompting the user to check their inbox or resend:
```json
{
  "status": "error",
  "data": {
    "email_verified": false
  },
  "error": "Email not verified. Please check your inbox or request a new verification link."
}
```
- `423` — Account locked. Response includes `locked_until` and `retry_after_seconds`:
```json
{
  "status": "error",
  "data": {
    "locked_until": "2026-09-07T10:15:00Z",
    "retry_after_seconds": 900
  },
  "error": "Account locked due to 3 failed login attempts. Try again in 15 minutes."
}
```

On each failed login, `failed_login_attempts` is incremented. After 3 consecutive failures, the account is locked for 15 minutes. A successful login resets the counter to 0.

---

### `POST /api/auth/forgot-password`

Request a password reset link. Sends an email with a time-limited reset token via Gmail SMTP. Always returns 200 regardless of whether the email exists (to prevent email enumeration).

**Auth:** None

**Request:**
```json
{
  "email": "john@example.com"
}
```

**Response:** `200 OK` (always, even if email not found)
```json
{
  "status": "success",
  "data": {
    "message": "If an account with that email exists, a reset link has been sent."
  },
  "error": null
}
```

**Side effects:**
- Generates a random token, stores its hash in `auth_tokens` with `type: "password_reset"` and a 15-minute expiry
- Sends an email with a link: `https://<frontend-url>/reset-password?token=<raw-token>`
- Previous unused tokens for this user are invalidated

---

### `POST /api/auth/reset-password`

Reset the user's password using a valid reset token.

**Auth:** None

**Request:**
```json
{
  "token": "raw-token-from-email-link",
  "new_password": "newsecurepassword"
}
```

**Response:** `200 OK`
```json
{
  "status": "success",
  "data": {
    "message": "Password has been reset successfully."
  },
  "error": null
}
```

**Side effects:**
- Updates the user's `password_hash`
- Marks the token as `used = true`
- Resets `failed_login_attempts = 0` and `locked_until = null`

**Errors:**
- `400` — Token is invalid, expired, or already used
- `422` — Validation error (password too short, etc.)

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

Start a new conversation with a selected role pack.

**Auth:** Any authenticated user

**Request:**
```json
{
  "role_pack": "hr | it | admissions",
  "title": "Leave balance inquiry"
}
```

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
      "active_slots": {}
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
      "active_slots": {}
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

## Admin — User Management

### `POST /api/admin/users`

Create a new admin account. The new admin is automatically scoped to the same department as the creator.

**Auth:** Admin only (`hr_admin`, `it_admin`, or `admissions_admin`)

**Request:**
```json
{
  "email": "newadmin@example.com",
  "password": "securepassword",
  "full_name": "Jane Smith"
}
```

**Response:** `201 Created`
```json
{
  "status": "success",
  "data": {
    "user_id": "uuid",
    "email": "newadmin@example.com",
    "full_name": "Jane Smith",
    "role": "hr_admin"
  },
  "error": null
}
```

**Errors:**
- `403` — Not an admin
- `409` — Email already registered

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
          "template_key": "leave_balance_response",
          "base_text": "You have {balance} days of leave remaining.",
          "allow_rephrasing": true,
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

Create a new intent with training phrases, a response template, and auto-generated variants. This is a synchronous call — the response includes the generated variants (~3–5 seconds due to Gemini API round-trip).

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "name": "check_leave_balance",
  "training_phrases": [
    "What's my leave balance?",
    "How many leaves do I have?",
    "Show me my remaining leaves",
    "Do I have any leave left?"
  ],
  "response_template": {
    "base_text": "You have {balance} days of leave remaining.",
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
      "name": "check_leave_balance",
      "role_pack": "hr",
      "needs_retrain": true,
      "training_phrases": [
        { "id": "uuid", "phrase_text": "What's my leave balance?" },
        { "id": "uuid", "phrase_text": "How many leaves do I have?" },
        { "id": "uuid", "phrase_text": "Show me my remaining leaves" },
        { "id": "uuid", "phrase_text": "Do I have any leave left?" }
      ],
      "response_template": {
        "id": "uuid",
        "template_key": "check_leave_balance_response",
        "base_text": "You have {balance} days of leave remaining.",
        "allow_rephrasing": true,
        "variants": [
          { "id": "uuid", "variant_text": "You have {balance} days of leave remaining." },
          { "id": "uuid", "variant_text": "Your current leave balance is {balance} days." },
          { "id": "uuid", "variant_text": "You've got {balance} leave days left." },
          { "id": "uuid", "variant_text": "There are {balance} days of leave available for you." },
          { "id": "uuid", "variant_text": "Your remaining leave stands at {balance} days." }
        ]
      }
    }
  },
  "error": null
}
```

The first variant is always the original `base_text`. The remaining 4 are generated by the Gemini API.

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
- `403` — Not an admin, or intent belongs to another role pack
- `404` — Intent not found
- `409` — New name already exists for this role pack

---

### `DELETE /api/admin/intents/:id`

Delete an intent and all its associated training phrases, response template, and variants. Sets `needs_retrain = true` for the role pack.

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
- `403` — Not an admin, or intent belongs to another role pack
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

## Admin — Retraining

### `POST /api/admin/retrain`

Trigger manual retraining for a role pack. Reads all intents and training phrases from the DB, converts to Rasa YAML, trains, and reloads the model. This is a long-running operation (~30–120 seconds depending on training data size).

**Auth:** Admin only (scoped to own role pack)

**Request:**
```json
{
  "role_pack": "hr"
}
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
