# V.A.R.I.O. — Project Briefing
**Voice Adaptive Role & Intent Orchestrator**
PES University · Jackfruit Mini-Project (UE24CS341A, Software Engineering) · Team PIPELINE (Project ID 42)
Team: Rohith G S, Kurumeti Mitesh, Mohammed Tahir Siddique, Pavan Kishor M

---

## 1. The problem (why this project exists)

Organizations like universities and companies get flooded with **repetitive, low-complexity, transactional queries** aimed at HR, IT Support, and Admissions — "What's my leave balance?", "How do I reset my password?", "What's my application status?" Answering these eats staff time that could go to higher-value work, and end users wait longer than they should for answers that are actually well-defined and repeatable.

The deeper inefficiency: when an organization wants a bot for HR *and* one for IT, they usually **build two separate systems from scratch**, duplicating the NLU engine, routing logic, and session management each time. There's no shared "brain" that can just be reconfigured per department.

**Who feels this pain:**
- **End users** (employees / students / applicants) — delayed answers to simple questions.
- **Role admins** (HR/IT/Admissions staff) — stuck answering the same questions instead of doing real work.
- **System admins / the org** — burden of maintaining N separate siloed chatbots.

---

## 2. The proposed solution (rough shape)

One **reusable core engine** (NLU, routing, session management) shared across all departments, plus **pluggable "role packs"** — independently configurable modules that carry each department's own vocabulary, intents, and workflows. A swappable **integration-adapter layer** sits between role packs and backend systems (HRMS/ITSM/Admissions), so today's mock APIs can later be swapped for real ones without touching core logic. Supports both **text and voice**.

---

## 3. Goals & success criteria (from the PRD)

| Criterion | Target |
|---|---|
| Performance | 95% of queries answered within 2 seconds (excluding artificial mock-API delay) |
| Scalability | 20 concurrent sessions in a live demo, no noticeable degradation |
| Extensibility | New role pack addable via **configuration only**, in under 1 developer-day, **no core-engine code changes** |
| Functional completeness | Every FR (leave submission, ticket creation, password reset, etc.) completable end-to-end via the conversational interface |

---

## 4. Users / stakeholders

| Stakeholder | Role |
|---|---|
| End User — Employee | HR queries (leave, policy) + IT support (tickets, password reset) |
| End User — Student/Applicant | Admissions queries (status, checklists, fees/deadlines) |
| Role Administrator (HR/IT/Admissions) | Manages intents/FAQs/workflows **for their own role pack only** |
| System Administrator (dev team) | Owns Core Engine + Integration Adapter layer, deploys/monitors |
| Course Instructor / Evaluator | Reviews and grades the artifacts + demo |

---

## 5. Scope

**In scope (v1):**
- Shared core NLU/routing engine
- Three role packs: **HR**, **IT Support**, **Admissions**
- Mocked internal-tool APIs (HRMS/ITSM/Admissions) behind a common adapter interface
- React web chat UI, text **and** voice (Web Speech API)
- Basic admin console for intents/FAQs per role

**Explicitly out of scope for v1** (all four docs agree):
- Real enterprise system integrations (mocks only)
- Multi-language support (English only)
- Native mobile app (responsive web only)
- Advanced analytics/BI dashboards (basic logs only)
- Proactive/push notifications (system only responds, never initiates)
- SSO for end users

---

## 6. Formal functional requirements (SRS)

**Core Engine**
- FR-1: Classify utterance → intent + confidence score
- FR-2: Below-threshold confidence → clarification prompt, not a workflow
- FR-3: New role packs registered via **config data**, no code/redeploy
- FR-4: Persist conversation context (role, intents, partial slots) across turns
- FR-5: Log every classification + routing decision for audit/demo traceability

**HR Role Pack**
- FR-6: Leave balance + leave-application status from mock HRMS
- FR-7: Answer HR policy FAQs from a curated knowledge base
- FR-8: Guided leave request (type, start, end, reason) with confirmation step
- FR-9: Return a unique reference ID on submission

**IT Support Role Pack**
- FR-10: Create ticket via mock ITSM (category, description, reporter) → ticket ID
- FR-11: Look up status of an existing ticket by ID
- FR-12: Guided password-reset flow with a mocked identity-verification step
- FR-13: Prevent duplicate ticket creation from an identical, immediately-repeated request in the same session

**Admissions Role Pack**
- FR-14: Application status lookup by application ID
- FR-15: Document checklist based on selected program
- FR-16: Fee/deadline FAQs from a single configurable admissions calendar
- FR-17: Graceful "not found" handling with a suggested next step

**Admin Configuration**
- FR-18: Authenticated Role Admin can add/edit/remove intents & FAQs — **own role pack only**
- FR-19: Role Admin can view conversation/workflow logs for their role

---

## 7. Non-functional requirements (SRS)

- **Performance:** 2s response for 95% of queries; 20 concurrent sessions with no degradation.
- **Safety:** No record-affecting workflow (leave approval, ticket closure) fires without explicit user confirmation; every triggering action is audit-logged (timestamp, user, action).
- **Security:** JWT on admin panel; role-based access (admins scoped to their own role pack); input validation/sanitization before NLU or persistence; no PII persisted beyond the session unless the workflow requires it.
- **Reliability:** Graceful degradation if a mock API is down (inform, don't crash); session context recoverable after a transient backend restart.
- **Usability:** Voice + text, with text as fallback when the browser lacks Web Speech API; jargon-free error/fallback messages.
- **Maintainability:** Core Engine, each Role Pack, and the Integration Adapter layer are separate, independently testable services.
- **Testability:** Every FR needs at least one test case (automated or manual).

---

## 8. Use cases (SRS §5)

| ID | Actor | Flow summary |
|---|---|---|
| UC-1 | Employee | Ask leave balance → intent classified → HRMS adapter call → balance returned in natural language |
| UC-2 | Employee | State leave intent → multi-turn slot fill (type/start/end/reason) → confirm → submit → reference ID |
| UC-3 | Employee | Describe issue → `raise_ticket` intent → category/description gathered → ITSM adapter creates ticket → ticket ID returned |
| UC-4 | Employee | Ask ticket status by ID → ITSM adapter query → status returned (or invalid-ID guidance) |
| UC-5 | Applicant | Ask application status by ID → Admissions adapter query → status + next steps |
| UC-6 | Role Admin | Log in (role-scoped JWT) → add/edit/remove intent or FAQ → change is live, no redeploy |

---

## 9. Architecture & tech stack (this is where the ADD has made concrete decisions beyond what the SRS/PRD left open)

> **Worth flagging:** research.md, PRD.md, and the SRS all list *"Rasa vs. spaCy"* as an **open question**. The ADD has since **resolved this** — the team committed to **Rasa Open Source**, running as **three separate instances** (one per role pack), rather than one shared classifier. Good to know so nobody re-litigates this mid-sprint.

### Confirmed stack (ADD.md)

| Layer | Technology |
|---|---|
| Frontend | Next.js (React), Web Speech API for browser-side STT |
| Backend | FastAPI (Python) |
| NLU | Rasa Open Source — 3 isolated instances (HR / IT / Admissions) |
| Database | PostgreSQL via Neon (serverless, free tier) |
| TTS | Google Cloud Text-to-Speech (Neural2 voices) |
| Response variant generation | Gemini API (Google AI Studio free tier) — paraphrases response templates |
| Compute hosting | Oracle Cloud Infrastructure Always Free (ARM Ampere A1, 4 OCPUs, 24GB RAM) |
| Frontend hosting | Vercel |
| Networking/HTTPS | Cloudflare Tunnel |
| Auth | Custom JWT, role claim embedded |
| Email | Gmail SMTP (`smtplib`, App Password) |
| Local dev | Docker Compose (full stack) |

### Additional engineering-process requirements (from SRS, not repeated in ADD but still binding)

- Git + GitHub, feature-branch workflow, **mandatory PR review**
- GitHub Projects or Jira for sprint/backlog tracking
- CI/CD via GitHub Actions or Jenkins on every PR
- Docker for consistent dev/demo environments
- Testing: pytest (backend), Jest/React Testing Library (frontend)
- Static analysis: SonarQube (or equivalent) before merge

### System layers (SRS §6 ↔ ADD architecture diagram — same idea, ADD names it more granularly)

```
Client Layer          → Next.js chat + admin console
API Gateway           → FastAPI, single entrypoint, auth, rate limiting, no business logic
Core Engine           → Session Manager + Conversation Store + Dialogue Router + Response Renderer
Role Packs            → 3x Rasa instances (HR, IT, Admissions)
Integration Adapters  → HRMSAdapter, ITSMAdapter, AdmissionsAdapter (common interface)
Mock Internal Systems → 3x FastAPI mock services standing in for real backends
PostgreSQL (Neon)     → single source of truth for everything, no in-memory cache
```

The whole point of this layering: **swap mocks for real HRMS/ITSM/Admissions later without touching Role Pack or Core Engine code.**

---

## 10. Modules (ADD.md — how the 4-person team can split work without merge conflicts)

| Module | Responsibility |
|---|---|
| `gateway` | Single HTTP entrypoint, schema validation, rate limiting, auth middleware, `{status, data, error}` envelope. No business logic. |
| `auth` | Registration (always `end_user` role, email-verification-gated), login (JWT with role claim, lockout after 3 failed attempts / 15 min), forgot-password (15-min token), admin creation by existing admins, seed script for first-deploy admins. |
| `session-manager` | Per-conversation state: active form, step, slots, TTL. Postgres is source of truth. |
| `conversation-store` | Durable conversation/message history for the dashboard. |
| `dialogue-router` | Pure dispatcher — reads `role_pack`, forwards to correct Rasa instance, passes result to renderer. No NLU logic itself. |
| `role-pack-runtime` | The 3 Rasa instances — intent classification, entity extraction, slot filling, action execution. |
| `integration-adapters` | One per department, common interface (`get_leave_balance()`, `create_ticket()`, etc.). Only code that knows it's talking to a mock. |
| `response-renderer` | `template_key` + `slot_values` → random stored variant → substitution. Pure DB read + string sub. |
| `tts-service` | Wraps Google Cloud TTS. Only for `mode: "talk"`. Degrades gracefully (flag → frontend falls back to text). |
| `admin-crud` | CRUD for intents/phrases/FAQs/templates, scoped by JWT role claim. Sets `needs_retrain = true`. Calls variant generator synchronously on template save. |
| `response-variant-generator` | Sends base text to Gemini for 4 paraphrased variants, validates placeholders survived, stores them. Admins can edit/delete individually. |
| `retraining-service` | Manual trigger only. Pulls intents+phrases for a role pack → Rasa YAML → `rasa train` → reload → clears `needs_retrain`. |
| `audit-log` | Write-only sink for business-significant events. Fire-and-forget. |

---

## 11. End-to-end flows

### Chat mode
User types → Frontend POSTs `/api/chat` → Gateway verifies JWT → Session Manager loads state from Postgres → message persisted to Conversation Store → Dialogue Router forwards to the right Rasa instance → Rasa may call an Integration Adapter → Adapter hits the relevant Mock API → slot filled → Rasa returns intent/entities/template/slots → Response Renderer picks a random stored variant and substitutes slot values → session updated, bot response persisted, event fired to Audit Log (async) → response returned to frontend.

### Talk mode (hands-free)
Same pipeline as chat, but: Browser STT (Web Speech API) transcribes speech → text goes through the identical chat flow → on the way back, Gateway calls the TTS Service → Google Cloud TTS synthesizes Neural2 audio → audio + text returned to frontend → played aloud → browser auto-restarts STT to listen again. If TTS credits are exhausted, it degrades to text-only with an error flag rather than breaking the loop.

### Admin flow (config + retraining)
Admin adds an intent + phrases + response template → Admin CRUD persists it and flags `needs_retrain = true` → **synchronously** calls the Response Variant Generator → Gemini paraphrases the base text into 4 variants (placeholders preserved and validated) → all 5 versions (original + 4) returned to the console for admin review/edit/delete. Retraining is a **separate, manual step**: admin clicks "Retrain," the service pulls that role pack's intents/phrases, converts to Rasa YAML, runs `rasa train`, reloads the live Rasa instance, and clears the retrain flag.

---

## 12. Data model (10 entities — ADD.md; full ERD referenced at `vario_database_erd.html`, not included in these docs)

| Entity | Key notes |
|---|---|
| `users` | `email_verified`, `failed_login_attempts`, `locked_until`; has many conversations/phrases/templates/audit entries/tokens |
| `conversations` | belongs to `users`; has many `messages`; has one `sessions` |
| `messages` | `sender` (user/bot), `intent_name`, `confidence`, `entities` (JSONB) |
| `sessions` | 1:1 with `conversations`; `current_form`, `current_step`, `slots` (JSONB), `expires_at` — Postgres is authoritative, no cache |
| `intents` | scoped by `role_pack`; `needs_retrain` flag |
| `training_phrases` | belongs to `intents`, authored by admin users |
| `response_templates` | `template_key`, `base_text`, `allow_rephrasing` flag |
| `response_variants` | belongs to a template; 4 auto-generated + original; individually editable/deletable |
| `auth_tokens` | shared table for both `email_verification` and `password_reset`, `type` discriminator, `used` flag, `expires_at` |
| `audit_log` | append-only; `action_type`, `reference_id`, `details` (JSONB) |

---

## 13. API contract (summary — full detail lives in `docs/api-contract.md` per ADD)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Register end user (unverified) |
| POST | `/api/auth/verify-email` | Verify via emailed token |
| POST | `/api/auth/resend-verification` | Resend verification email |
| POST | `/api/auth/login` | Login → JWT (blocks unverified, locks after 3 fails) |
| POST | `/api/auth/forgot-password` | Request reset link |
| POST | `/api/auth/reset-password` | Reset via valid token |
| GET/POST | `/api/conversations` | List / start conversations |
| GET | `/api/conversations/:id/messages` | Fetch history |
| POST | `/api/chat` | Send a message (chat or talk mode) |
| POST | `/api/admin/users` | Create admin for creator's department |
| GET/POST/PUT/DELETE | `/api/admin/intents[/:id]` | Manage intents (+ auto variant generation on create) |
| GET/PUT | `/api/admin/templates[/:id]` | Manage response templates |
| PUT/DELETE | `/api/admin/variants/:id` | Edit/delete a generated variant |
| POST | `/api/admin/retrain` | Trigger manual retraining |
| GET | `/api/admin/retrain/:job_id` | Check retrain job status |
| GET | `/api/admin/audit-log` | View audit entries |

---

## 14. Constraints & assumptions worth keeping in mind

- Team of 4, one semester, alongside other coursework — scope is deliberately tight.
- No access to real HRMS/ITSM/Admissions — everything is mocked but behind a documented adapter interface so the swap is theoretically painless later.
- English only, web only, no SSO, no push notifications — don't scope-creep into these.
- Expected load is **20 concurrent sessions for a demo**, not production traffic — infra choices (OCI free tier, Neon free tier, Gemini free tier) reflect that.
- Assumes a few hundred hand-labelled training examples per intent will be "good enough" for Rasa accuracy within scope.
- Password reset tokens: 15-min expiry. Email verification tokens: 24-hour expiry. Account lockout: 3 failed attempts → 15-minute lock.

---

## 15. Future enhancements (explicitly deferred, not v1 work)

- Real HRMS/ITSM/Admissions integrations via the existing adapter interface
- Multi-language support
- Additional role packs (Finance, Facilities, Library) to prove extensibility further
- Analytics dashboard (query volume, top intents, fallback rate, completion rate)
- Native mobile app
- Proactive/outbound notifications (e.g., ticket status changes)
- Feedback loop surfacing low-confidence/misclassified intents to admins
- SSO

---

## 16. Quick gap-check across the four documents

- **NLU decision:** research/PRD/SRS pose it as open; ADD has already decided (Rasa, 3 instances). Treat this as settled.
- **Auth depth:** SRS only formally requires JWT auth for the **admin panel**; ADD builds out a full end-user auth system too (registration, email verification, lockout, password reset) — this is a reasonable elaboration since several use cases (UC-2, UC-3) require an authenticated/identified end user, but it's worth the team confirming this expanded scope is intentional and budgeted for in the timeline.
- **ERD file:** ADD references `vario_database_erd.html` for the full diagram — that file wasn't among the four docs provided, so the 10-entity summary above is inferred from the ADD's prose description, not the diagram itself.
- **Open questions still genuinely unresolved:** the exact mock identity-verification mechanism for IT password reset (PRD/SRS both flag this), and the precise DB schema strategy for isolating role-pack config while sharing the sessions table.
