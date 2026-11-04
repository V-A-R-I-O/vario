# Integration Audit 2 — Defect Log

**Date:** 2026-11-04 · **Baseline:** `main` @ `daaee87` (EPIC-5 slices merged except slice-34)

## Method

- Ran every suite on `main`: backend 163, frontend 86 (lint, tsc and build clean), mocks, role packs, rasa-shared, Jira-sync script.
- Trained all three Rasa models (`rasa train`) and ran the stack natively, with HR and IT on **real Rasa 3.6.20** using each pack's own `credentials.yml`/`endpoints.yml`.
- Replayed the EPIC-5 bug repros through `POST /api/chat`, checked PostgreSQL and Rasa's tracker store directly, and rendered every stored card through the UI components.

## Verified fixed on real Rasa

| Area | Verified |
|---|---|
| HR | Own balance without asking (B6) · typed employee IDs ignored (M2a) · every leave question asked again (M1a) · natural dates (N5) · leave status (N8) · WFH text matches mock (M7a) · HRMS outage message (B2a) · greet/goodbye (M5a) |
| IT | Cancel leaves the ticket prompt (M3b) · "still open?" → status (M4c) · IT-#### examples (M7b) · ticket ID in text (N9) · it@ creates tickets (M7c) · reset limited to the signed-in account · security answer redacted in the gateway **and** Rasa's tracker store |
| Admissions (keyword runtime) | Topic switching (M3c) · follow-ups (N13) · answers from the mock (B2b) · greet/goodbye (M5b) |
| Admin | Variants kept on save (M9a) · seeded variants deletable (M9b) · admin changes audited (M9c) |
| Gateway | Degraded reply when a pack is down (M6) · single Alembic head · seed works |

## Still open from EPIC-5

SCRUM-60 (B1), SCRUM-61 (B3), SCRUM-62 (B4), SCRUM-63 (N3), SCRUM-64 (N4) — slice-34 · SCRUM-70 (M3a) and SCRUM-71 (M4a) — slice-35 · SCRUM-74 (M4b) — slice-36 · SCRUM-101 (N12) — slice-10.

## New defects (20)

| ID | Severity | Summary | Fixed by |
|---|---|---|---|
| A2-01 | Blocker | Gateway crashes at startup on PostgreSQL | slice-34-local-demo-stack (SCRUM-44) |
| A2-02 | Blocker | rasa-hr cannot start: endpoints.yml uses unsupported ${VAR:-default} syntax | slice-34-local-demo-stack (SCRUM-44) |
| A2-03 | Blocker | Every IT custom action fails: quoted action endpoint is never expanded | slice-34-local-demo-stack (SCRUM-44) |
| A2-05 | Blocker | Admissions Rasa model fails to train; runtime is still the keyword server.py | slice-39-adm-real-rasa (SCRUM-49) |
| A2-06 | Blocker | Leave start date is overwritten by the end date | slice-35-hr-real-rasa (SCRUM-45) |
| A2-07 | Blocker | HR cards without options/rows crash the chat page | slice-35-hr-real-rasa (SCRUM-45) |
| A2-08 | Major | HR image still runs the FastAPI server.py, not Rasa | slice-35-hr-real-rasa (SCRUM-45) |
| A2-09 | Minor | mock-hrms tests hard-code November 2026 dates and now fail | slice-36-hr-data-fixes (SCRUM-46) |
| A2-10 | Major | IT ticket and password-reset audit entries are blank ('unknown') | slice-37-it-real-rasa (SCRUM-47) |
| A2-11 | Major | IT 'ticket created' and 'reset initiated' cards render empty | slice-37-it-real-rasa (SCRUM-47) |
| A2-12 | Minor | IT confirmation shows no ticket details | slice-37-it-real-rasa (SCRUM-47) |
| A2-13 | Minor | Password reset loops forever after entering another employee's ID | slice-37-it-real-rasa (SCRUM-47) |
| A2-14 | Major | Gateway accepts cards with missing required fields | slice-32-rasa-contract-v2 (SCRUM-42) |
| A2-15 | Major | One malformed card crashes the whole chat page | slice-33-chat-ui-hardening (SCRUM-43) |
| A2-16 | Major | Retraining does not work on real Rasa for any pack | slice-10-retraining (SCRUM-31) |
| A2-17 | Minor | Compose never passes Gemini, TTS or retraining settings to the gateway | slice-34-local-demo-stack (SCRUM-44) |
| A2-18 | Trivial | Rephraser defaults to the retired gemini-1.5-flash model | slice-34-local-demo-stack (SCRUM-44) |
| A2-19 | Minor | rasa-shared tests are not run in CI | slice-34-local-demo-stack (SCRUM-44) |
| A2-20 | Minor | Form answers report the intent of the message that started the form | slice-32-rasa-contract-v2 (SCRUM-42) |
| A2-21 | Major | 'cancel' cannot end IT ticket creation or password reset | slice-37-it-real-rasa (SCRUM-47) |

## Details

### A2-01 — Gateway crashes at startup on PostgreSQL

Blocker · fixed by `slice-34-local-demo-stack`

Steps:
1. Start the gateway against PostgreSQL (DATABASE_URL=postgresql+asyncpg://...).

- **Actual:** Application startup fails: recover_stale_jobs() binds a timezone-aware datetime to a TIMESTAMP WITHOUT TIME ZONE column and asyncpg raises DataError. Tests use SQLite, which accepts it, so CI is green.
- **Expected:** The gateway starts on PostgreSQL; retraining timestamps are naive UTC like every other column.
- **Where:** `backend/app/services/retraining_service.py:31-32`

### A2-02 — rasa-hr cannot start: endpoints.yml uses unsupported ${VAR:-default} syntax

Blocker · fixed by `slice-34-local-demo-stack`

Steps:
1. rasa run --endpoints rasa-hr/endpoints.yml (with RASA_ACTION_ENDPOINT_URL set).

- **Actual:** RasaException: Error when trying to expand the environment variables in '${RASA_ACTION_ENDPOINT_URL:-http://localhost:5055/webhook}'. Rasa only supports ${VAR}.
- **Expected:** Plain ${VAR} references, with the values supplied by docker compose.
- **Where:** `rasa-hr/endpoints.yml:3, 8-11`

### A2-03 — Every IT custom action fails: quoted action endpoint is never expanded

Blocker · fixed by `slice-34-local-demo-stack`

Steps:
1. Start rasa-it with ACTION_ENDPOINT_URL set.
2. Ask "check my ticket status".

- **Actual:** Rasa calls the literal URL ${ACTION_ENDPOINT_URL} (quoted YAML strings are not expanded), so every custom action errors and the gateway replies 'Sorry, I couldn't put together a response'. Only 'hi' works.
- **Expected:** The action endpoint resolves and IT flows work.
- **Where:** `rasa-it/endpoints.yml:2`

### A2-05 — Admissions Rasa model fails to train; runtime is still the keyword server.py

Blocker · fixed by `slice-39-adm-real-rasa`

Steps:
1. cd rasa-admissions && rasa train

- **Actual:** InvalidRule: 5 contradictions between stories and the form-activation rules (application_status_form, checklist_form). `rasa data validate` passes and CI never trains, so CI is green. The Dockerfile still runs server.py, and endpoints.yml has no tracker store.
- **Expected:** The model trains; Admissions runs on real Rasa with an action server and the redacting tracker store, like HR and IT.
- **Where:** `rasa-admissions/data/stories.yml, data/rules.yml, Dockerfile, endpoints.yml`

### A2-06 — Leave start date is overwritten by the end date

Blocker · fixed by `slice-35-hr-real-rasa`

Steps:
1. Apply for annual leave: start 2026-11-20, end 2026-11-21, any reason, confirm.

- **Actual:** Confirmation shows '2026-11-21 to 2026-11-21' and mock-HRMS stores start 2026-11-21: the end-date answer is extracted as a start_date entity and refills start_date.
- **Expected:** Dates are stored exactly as entered.
- **Where:** `rasa-hr/domain.yml start_date / end_date slot mappings`

### A2-07 — HR cards without options/rows crash the chat page

Blocker · fixed by `slice-35-hr-real-rasa`

Steps:
1. Start a leave request in the browser; reach the start-date prompt or the confirmation.

- **Actual:** HR sends slot_prompt cards with no `options` and a confirmation with no `rows`; the UI throws 'Cannot read properties of undefined (reading map)' and the page crashes.
- **Expected:** Every HR card matches the ADR-006 BotMessageData shape; the confirmation lists the request details.
- **Where:** `rasa-hr/actions/actions.py (vario_payload cards)`

### A2-08 — HR image still runs the FastAPI server.py, not Rasa

Major · fixed by `slice-35-hr-real-rasa`

Steps:
1. Build rasa-hr/Dockerfile.

- **Actual:** The image runs uvicorn server:app (keyword runtime); there is no Rasa server/action-server image, so compose cannot run HR on real Rasa.
- **Expected:** A real-Rasa HR image (server + action server) like IT's.
- **Where:** `rasa-hr/Dockerfile`

### A2-09 — mock-hrms tests hard-code November 2026 dates and now fail

Minor · fixed by `slice-36-hr-data-fixes`

Steps:
1. Run mock-hrms-service tests after 2026-11-01.

- **Actual:** 2 tests fail: the mock correctly rejects start_date 2026-11-01 as past. The next PR's CI goes red.
- **Expected:** Tests compute dates relative to today.
- **Where:** `mock-hrms-service/tests/test_mock_hrms.py:103-147`

### A2-10 — IT ticket and password-reset audit entries are blank ('unknown')

Major · fixed by `slice-37-it-real-rasa`

Steps:
1. Create a ticket or complete a password reset; open the IT audit log.

- **Actual:** Entries have action_type 'unknown', no reference and no details: IT sends audit_event {type, ticket_id, ...} instead of ADR-006 {action_type, reference_id, details}.
- **Expected:** ticket_created / password_reset_initiated entries with the ticket or employee as reference.
- **Where:** `rasa-it/actions/actions.py:165, 262`

### A2-11 — IT 'ticket created' and 'reset initiated' cards render empty

Major · fixed by `slice-37-it-real-rasa`

Steps:
1. Create a ticket in the browser.

- **Actual:** IT result cards carry `message`/`ticket_id` instead of `text`/`referenceId`, so the UI shows an empty success card and the ticket ID is invisible.
- **Expected:** Result cards use the ADR-006 shape: text plus referenceId.
- **Where:** `rasa-it/actions/actions.py result cards`

### A2-12 — IT confirmation shows no ticket details

Minor · fixed by `slice-37-it-real-rasa`

Steps:
1. Raise a ticket and reach the confirmation step.

- **Actual:** The reply says 'Please review your request' but the card is a slot_prompt with only Confirm/Cancel — nothing to review.
- **Expected:** A confirmation card listing category, description and reporter.
- **Where:** `rasa-it/actions/actions.py`

### A2-13 — Password reset loops forever after entering another employee's ID

Minor · fixed by `slice-37-it-real-rasa`

Steps:
1. As EMP-1012, start a reset and enter EMP-1001, then type anything.

- **Actual:** Every reply repeats 'only available for your signed-in employee account' and re-asks; even restarting the request loops.
- **Expected:** Explain once and offer to reset the signed-in account, or exit the flow; cancel works.
- **Where:** `rasa-it/actions/actions.py validate_employee_id`

### A2-14 — Gateway accepts cards with missing required fields

Major · fixed by `slice-32-rasa-contract-v2`

Steps:
1. Have a role pack return {"type": "confirmation"} with no rows.

- **Actual:** The gateway only checks `type`, passes the card through, and the UI crashes on it.
- **Expected:** Cards missing required fields are dropped (text reply used) and logged.
- **Where:** `backend/app/services/dialogue_router.py _valid_card`

### A2-15 — One malformed card crashes the whole chat page

Major · fixed by `slice-33-chat-ui-hardening`

Steps:
1. Render a slot_prompt card without options (or a data card without rows).

- **Actual:** TypeError during render unmounts the page.
- **Expected:** A malformed card falls back to the reply text; the page keeps working.
- **Where:** `frontend/src/lib/chatCards.ts, src/components/chat/messages.tsx`

### A2-16 — Retraining does not work on real Rasa for any pack

Major · fixed by `slice-10-retraining`

Steps:
1. As it_admin (with RETRAINING_INTERNAL_TOKEN set), POST /api/admin/retrain and poll the job.

- **Actual:** IT calls /internal/retrain, which only the old server.py had (404 on Rasa). HR/Admissions POST multipart files to /model/train (Rasa 3.6 accepts a YAML body) and call /model/reload, which doesn't exist. Admin-created FAQs therefore never get answered.
- **Expected:** Retraining posts Rasa YAML to /model/train and loads the new model with PUT /model; a new FAQ is answered afterwards.
- **Where:** `backend/app/services/retraining_service.py:97-120`

### A2-17 — Compose never passes Gemini, TTS or retraining settings to the gateway

Minor · fixed by `slice-34-local-demo-stack`

Steps:
1. Fill GEMINI_API_KEY / GOOGLE_APPLICATION_CREDENTIALS in .env; docker compose up.

- **Actual:** The gateway service lists neither variable, so the rephraser and talk-mode audio stay off; no secrets mount exists for the TTS key file.
- **Expected:** Optional settings flow from .env into the gateway; a read-only secrets mount for the TTS key.
- **Where:** `docker-compose.yml gateway environment`

### A2-18 — Rephraser defaults to the retired gemini-1.5-flash model

Trivial · fixed by `slice-34-local-demo-stack`

Steps:
1. Configure GEMINI_API_KEY without GEMINI_MODEL.

- **Actual:** The default model name is from the Gemini 1.5 generation, which Google has retired; generation would fail and fall back to the original text.
- **Expected:** A current default model, overridable via GEMINI_MODEL in .env.example.
- **Where:** `backend/app/config.py GEMINI_MODEL`

### A2-19 — rasa-shared tests are not run in CI

Minor · fixed by `slice-34-local-demo-stack`

Steps:
1. Read .github/workflows/ci.yml.

- **Actual:** The shared channel, tracker-store redaction and contract tests (31) only run locally.
- **Expected:** CI runs rasa-shared tests on Python 3.10.
- **Where:** `.github/workflows/ci.yml`

### A2-20 — Form answers report the intent of the message that started the form

Minor · fixed by `slice-32-rasa-contract-v2`

Steps:
1. Run a pack with Rasa's in-memory tracker store (no tracker_store, or Postgres unreachable when Rasa starts).
2. Say "my laptop screen is broken", then "cancel", then "hardware".

- **Actual:** Every reply reports raise_ticket 0.97: the channel reads tracker.latest_message from a tracker rebuilt from applied events, and Rasa folds happy-path form turns out of those. The gateway stores and logs the wrong intent, confidence and entities for each form answer.
- **Expected:** The reply describes the message just handled (cancel 0.76, then inform 1.0).
- **Where:** `rasa-shared/vario_rasa/channel.py (tracker.latest_message)`

### A2-21 — 'cancel' cannot end IT ticket creation or password reset

Major · fixed by `slice-37-it-real-rasa`

Steps:
1. Say "my laptop screen is broken", then "cancel".

- **Actual:** The category slot takes 'cancel' as its value, validation re-asks 'Choose hardware, software, ...', and the cancel/goodbye/greet rules never run. The same happens at the description, employee-ID and security-answer steps.
- **Expected:** Cancel, goodbye and greet end the form at any step.
- **Where:** `rasa-it/domain.yml from_text slot mappings`

## Flagged, not fixed

- Any signed-in applicant can look up any application ID in Admissions. FR-14 specifies lookup by ID, so this is treated as by design for the mock; revisit if evaluators ask about authorization.
- slice-31 (perf-hardening) has no PR yet.
