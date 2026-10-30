# Sprint 3 Integration Audit — Test Report & Defect Log

**Date:** 2026-10-29 · **Baseline:** `main` @ `83ed213` (end of Sprint 3) · **Epic:** EPIC-5 Integration Defects & Real Rasa Migration · **Slices:** 32–40

## Summary

Every automated suite passes, yet core end-to-end flows break once all services run together, because each suite mocks the service next to it. The audit also found that the three "Rasa" role packs are hand-written keyword matchers, not Rasa Open Source.

Decisions taken by the team after this audit:

1. **Migrate all three role packs to real Rasa Open Source 3.6.20.** Each pack gets a Rasa server and an action server. The gateway↔Rasa contract stays stable via a custom input channel (ADR-006, slice-32).
2. **Demo locally instead of deploying.** The stack runs on laptop C (Windows 11, 24 GB, Docker). Other laptops join over a hotspot, or over a temporary HTTPS tunnel for voice. OCI/Cloudflare/Vercel/Neon (slices 29/30) are **Won't Do**; ADR-007 is written in slice-34.
3. **Sprint 4 priorities:** EPIC-5 first. Keep slice-10 (retraining, now meaningful on real Rasa) and keep slice-31 minimal. Slice-09 (rephraser) is "if time".

## Method

1. Ran every test suite on `main`.
2. Started all 8 services natively on a seeded database: mock-auth, mock-hrms, mock-itsm, mock-admissions, rasa-hr, rasa-it, rasa-admissions and the gateway.
3. Drove real conversations through `POST /api/chat` and the admin API as each seeded user.
4. Ran four parallel reviews (HR, IT, Admissions, frontend). Each re-ran its pack against its real mock and ported the chat page's card logic to check what the UI would render.
5. Stopped services on purpose to test degradation.

Defects marked *reproduced by running* were observed live; *found by reading* were confirmed from code.

## Automated test results (baseline)

| Suite | Result |
|---|---|
| backend (pytest) | 134 passed |
| frontend (Jest) | 60 passed · lint OK (1 warning) · `next build` OK |
| rasa-hr | 33 passed |
| rasa-it | 21 passed, **9 silently skipped** (no async test plugin) |
| rasa-admissions | 29 passed (ran against hardcoded fallback data, not the mock) |
| mock-auth / mock-hrms / mock-itsm / mock-admissions | 4 / 12 / 7 / 12 passed (only mock-auth runs in CI) |

## Verified working

- **IT security answers:** never stored in messages, `sessions.slots`, API responses, entities or logs.
- **FR-13 duplicate-ticket suppression** works.
- **IT ticket reporter:** taken from the trusted identity, not from chat text.
- **Admin scoping:** each admin sees only their own role pack; cross-pack access returns 403.
- **Login and logout:** an expired or invalid token sends the user back to the login page; logout works.
- **Template edits** show up in chat immediately.
- **Talk mode fallback:** degrades cleanly to text when no text-to-speech credentials are set.
- **Leave flow safety:** nothing is submitted without an explicit confirm (NFR safety).
- **Ticket creation** writes a `ticket_created` audit entry.

## Defect log

51 defects. Severity: **Blocker** = demo breaks · **Major** = wrong/visible in a demo · **Minor** · **Trivial**.

| ID | Severity | Summary | Fixed by | Owner |
|---|---|---|---|---|
| [B5a](#b5a) | Blocker | Session slots accumulate forever; every reply returns all past values | slice-32-rasa-contract-v2 | Tahir |
| [B5b](#b5b) | Blocker | Chat page picks cards from accumulated session slots, so stale cards replace later replies | slice-33-chat-ui-hardening | Tahir |
| [B1](#b1) | Blocker | docker compose does not run the real stack | slice-34-local-demo-stack | Tahir |
| [B3](#b3) | Blocker | Database is never migrated or seeded automatically, and seeding is undocumented | slice-34-local-demo-stack | Tahir |
| [B4](#b4) | Blocker | Frontend can't reach the API from other laptops (localhost baked into the bundle) | slice-34-local-demo-stack | Tahir |
| [B6](#b6) | Blocker | HR ignores the logged-in employee: balance loops and leave submission always fails | slice-35-hr-real-rasa | Pavan Kishor |
| [B7](#b7) | Blocker | Every leave-request question shows 'Sorry, I couldn't put together a response' | slice-35-hr-real-rasa | Pavan Kishor |
| [B2a](#b2a) | Blocker | HR pack imports backend code and silently serves hardcoded data when that fails | slice-35-hr-real-rasa | Pavan Kishor |
| [B2b](#b2b) | Blocker | Admissions pack never calls mock-admissions; answers are hardcoded (FR-16 broken) | slice-39-adm-real-rasa | Mitesh |
| [B8](#b8) | Blocker | Admin conversation-logs page expects field names the backend doesn't send | slice-40-admin-console-fixes | Mitesh |
| [N12](#n12) | Major | Admin-created FAQ intents are never answered (no retrain path) | slice-10-retraining | Rohith |
| [M6](#m6) | Major | Role-pack outage returns HTTP 500, loses the user's message and has no CORS header | slice-32-rasa-contract-v2 | Tahir |
| [M12](#m12) | Major | Cards break after a page reload because card data isn't stored with the message | slice-33-chat-ui-hardening | Tahir |
| [M8](#m8) | Major | Talk mode gets stuck on 'Listening…' and doesn't detect insecure origins | slice-33-chat-ui-hardening | Tahir |
| [M10](#m10) | Major | Double-clicking Confirm or an option button sends the message twice | slice-33-chat-ui-hardening | Tahir |
| [N3](#n3) | Major | Rate limits break a multi-laptop demo (shared IP behind proxy, single demo account) | slice-34-local-demo-stack | Tahir |
| [M1a](#m1a) | Major | A second leave request reuses the previous request's dates and reason | slice-35-hr-real-rasa | Pavan Kishor |
| [M2a](#m2a) | Major | Any user can read another employee's leave balance and file leave as them | slice-35-hr-real-rasa | Pavan Kishor |
| [M3a](#m3a) | Major | Leave form gets stuck after an off-script reply at the confirmation step | slice-35-hr-real-rasa | Pavan Kishor |
| [M4a](#m4a) | Major | Off-topic policy questions get the leave policy at 0.9 confidence | slice-35-hr-real-rasa | Pavan Kishor |
| [M5a](#m5a) | Major | HR replies with 'Intent greet acknowledged' debug text | slice-35-hr-real-rasa | Pavan Kishor |
| [M4b](#m4b) | Major | Topic-specific HR FAQ answers are replaced by the generic policy template | slice-36-hr-data-fixes | Pavan Kishor |
| [N8](#n8) | Major | Leave request status (FR-6) is a stub | slice-36-hr-data-fixes | Pavan Kishor |
| [M3b](#m3b) | Major | Ticket-ID prompt traps the user; even 'cancel' is rejected | slice-37-it-real-rasa | Rohith |
| [M4c](#m4c) | Major | Ticket status questions start a new ticket instead | slice-37-it-real-rasa | Rohith |
| [B5c](#b5c) | Major | IT replies carry the previous ticket's status, so cards show the wrong ticket | slice-37-it-real-rasa | Rohith |
| [M7b](#m7b) | Major | Bot asks for TKT-1234 but every ticket ID is IT-10xx | slice-38-it-data-and-ci | Rohith |
| [M7c](#m7c) | Major | IT and Admissions admin logins don't exist in mock-ITSM, so ticket creation loops | slice-38-it-data-and-ci | Rohith |
| [M3c](#m3c) | Major | A pending Admissions prompt swallows the next message | slice-39-adm-real-rasa | Mitesh |
| [M1b](#m1b) | Major | Admissions reuses stale application IDs and programs | slice-39-adm-real-rasa | Mitesh |
| [M5b](#m5b) | Major | Admissions replies with 'Intent greet acknowledged' debug text | slice-39-adm-real-rasa | Mitesh |
| [M9a](#m9a) | Major | Saving an intent wipes its stored reply variants | slice-40-admin-console-fixes | Mitesh |
| [M11](#m11) | Minor | Sidebar conversation list never refreshes; admins have no link to the console | slice-33-chat-ui-hardening | Tahir |
| [N2](#n2) | Minor | Every chat error shows 'Connection lost'; failed messages have no retry | slice-33-chat-ui-hardening | Tahir |
| [N4](#n4) | Minor | Docs describe the dropped cloud deployment and an unstarted project | slice-34-local-demo-stack | Tahir |
| [N5](#n5) | Minor | Leave form rejects 'annual' and natural-language dates | slice-35-hr-real-rasa | Pavan Kishor |
| [M7a](#m7a) | Minor | HR FAQ answers contradict the mock HRMS policy data | slice-36-hr-data-fixes | Pavan Kishor |
| [N6](#n6) | Minor | mock-hrms /reset does not restore leave balances | slice-36-hr-data-fixes | Pavan Kishor |
| [N7](#n7) | Minor | mock-hrms accepts invalid leave requests | slice-36-hr-data-fixes | Pavan Kishor |
| [M2b](#m2b) | Minor | Password-reset retry limit resets when the flow restarts (unlimited guesses) | slice-37-it-real-rasa | Rohith |
| [N9](#n9) | Minor | 'Ticket created' reply has no ticket ID; 'check my ticket status' reuses the last ID | slice-37-it-real-rasa | Rohith |
| [N10](#n10) | Minor | IT pack runs on the wrong Python for Rasa, with unpinned deps and a duplicate adapter | slice-37-it-real-rasa | Rohith |
| [N11](#n11) | Minor | CI gaps: mock-service tests never run, 9 IT tests silently skipped, no Rasa validation | slice-38-it-data-and-ci | Rohith |
| [M6b](#m6b) | Minor | Admissions reports 'not found' when the service is actually down | slice-39-adm-real-rasa | Mitesh |
| [N13](#n13) | Minor | Admissions misclassifies common follow-up questions | slice-39-adm-real-rasa | Mitesh |
| [M9b](#m9b) | Minor | Seeded reply variants can't be deleted | slice-40-admin-console-fixes | Mitesh |
| [M9c](#m9c) | Minor | Admin configuration changes are not audit-logged | slice-40-admin-console-fixes | Mitesh |
| [N15](#n15) | Minor | Conversation-log filters fire on every keystroke; the 'to' date excludes that day | slice-40-admin-console-fixes | Mitesh |
| [N1](#n1) | Trivial | sessions.expires_at is written but never enforced | slice-32-rasa-contract-v2 | Tahir |
| [N14](#n14) | Trivial | Admissions card components are dead code duplicated in the chat page | slice-39-adm-real-rasa | Mitesh |
| [N16](#n16) | Trivial | 'Retraining' nav item links to a page that doesn't exist | slice-40-admin-console-fixes | Mitesh |

### Load per owner

| Owner | Slices | Points | Bugs |
|---|---|---|---|
| Tahir (D) | 32, 33, 34 | 13 | 14 |
| Pavan Kishor (A) | 35, 36 | 11 | 14 |
| Rohith (B) | 37, 38 | 11 | 10 |
| Mitesh (C) | 39, 40 | 11 | 13 |

## Defect details

### B5a

**Session slots accumulate forever; every reply returns all past values** — Blocker · fixed by `slice-32-rasa-contract-v2` · reproduced by running

Steps:
1. Log in as emp1@org.example.com and open an HR conversation.
2. Send "what is my leave balance for EMP-1042".
3. Send "can I work from home?".

- **Actual:** session.slots on the WFH reply still contains total/casual/sick/earned and employee_id from the previous turn. The role packs also re-merge stored slots, so values from any earlier workflow leak into every later turn (this drives the stale-card bugs B5b/B5c and M1a/M1b).
- **Expected:** Each response carries only the current turn's values; workflow values are cleared when a workflow completes or is cancelled (Rasa tracker owns dialogue state per ADR-006).
- **Where:** `backend/app/services/session_manager.py:54-56 (merge, never delete)`

### M6

**Role-pack outage returns HTTP 500, loses the user's message and has no CORS header** — Major · fixed by `slice-32-rasa-contract-v2` · reproduced by running

Steps:
1. Stop the rasa-hr service.
2. Send any message in an HR conversation.

- **Actual:** 500 'Internal server error'. The user's message is not persisted (transaction rolled back). The response has no Access-Control-Allow-Origin header, so the browser reports a network error and the UI shows 'Connection lost'.
- **Expected:** Friendly bot reply (e.g. 'The HR assistant is unavailable right now, please try again shortly'), user message kept, CORS headers present, degraded flag set (NFR reliability).
- **Where:** `backend/app/services/dialogue_router.py (_post_to_rasa raises); backend/app/main.py (Exception handler runs outside CORS middleware)`

### N1

**sessions.expires_at is written but never enforced** — Trivial · fixed by `slice-32-rasa-contract-v2` · found by reading

Steps:
1. Read session_manager.load_or_create.

- **Actual:** expires_at is refreshed every turn but never checked, so sessions never expire.
- **Expected:** Expired sessions reset dialogue state, or the field is removed in favour of Rasa session_config (ADR-006 decides).
- **Where:** `backend/app/services/session_manager.py:21-38`

### B5b

**Chat page picks cards from accumulated session slots, so stale cards replace later replies** — Blocker · fixed by `slice-33-chat-ui-hardening` · reproduced by running

Steps:
1. HR: send "leave balance for EMP-1042", then "can I work from home?", then "I want to apply for leave".
2. Admissions: ask for the MBA document checklist, then "status of APP-1001".
3. IT: look up IT-1001, then send "check my ticket status".

- **Actual:** Later replies render as the earlier card: the balance card replaces the WFH answer and every leave prompt (so Confirm/Cancel never appears), the document list replaces the status card, and the ticket card shows 'TKT-1234: In Progress' parsed from the prompt text.
- **Expected:** Each reply renders from that turn's own card data (ADR-006 card field), dispatched by card type — no slot-key sniffing and no regex on reply text.
- **Where:** `frontend/src/app/home/chat/[id]/page.tsx lines 118, 229, 286, 317-325, 422-429`

### M12

**Cards break after a page reload because card data isn't stored with the message** — Major · fixed by `slice-33-chat-ui-hardening` · reproduced by running

Steps:
1. Admissions: ask "what documents do I need for MBA?".
2. Reload the page.

- **Actual:** The checklist reopens as a 'pick a program' prompt with B.Tech/M.Tech/MBA buttons. Some not-found replies render as a status card with an invented 'Under Review' status. Leave cards degrade to plain text.
- **Expected:** Cards reload exactly as they rendered live (card persisted per message by slice-32).
- **Where:** `frontend/src/app/home/chat/[id]/page.tsx:75-82, 258-260, 395-396`

### M8

**Talk mode gets stuck on 'Listening…' and doesn't detect insecure origins** — Major · fixed by `slice-33-chat-ui-hardening` · reproduced by running

Steps:
1. Open http://<LAN-IP>:3000 from another laptop (or deny mic permission).
2. Start talk mode.

- **Actual:** The speech-recognition 'not-allowed' error only clears the listening flag, so the overlay shows 'Listening…' forever with no message. The mic button is enabled on insecure origins. A failed send also leaves talk mode active.
- **Expected:** isSecureContext check with a clear 'voice needs HTTPS or localhost' message; any recognition error or failed send closes the overlay with a message and a retry option.
- **Where:** `frontend/src/lib/useSpeechRecognition.ts:81; frontend/src/app/home/chat/[id]/page.tsx:174-177`

### M10

**Double-clicking Confirm or an option button sends the message twice** — Major · fixed by `slice-33-chat-ui-hardening` · reproduced by running

Steps:
1. IT: raise a ticket and reach the Confirm card.
2. Double-click Confirm.

- **Actual:** 'confirm' is sent twice; old cards remain clickable. On /home/new a double-click creates two conversations.
- **Expected:** Buttons are disabled while a send is in flight and once answered; new-conversation creation is guarded.
- **Where:** `frontend/src/components/chat/messages.tsx:76; page.tsx:481, 500, 536, 600; frontend/src/app/home/new/page.tsx`

### M11

**Sidebar conversation list never refreshes; admins have no link to the console** — Minor · fixed by `slice-33-chat-ui-hardening` · found by reading

Steps:
1. Create a new conversation and send messages.
2. Log in as hr@org.example.com.

- **Actual:** The new conversation doesn't appear in the sidebar until a full reload, and previews stay stale. Admins land on /home with no way to reach /admin except typing the URL.
- **Expected:** Sidebar refreshes after create/send; admin roles see an 'Admin console' link.
- **Where:** `frontend/src/app/home/layout.tsx:15-38; frontend/src/components/LoginForm.tsx:25`

### N2

**Every chat error shows 'Connection lost'; failed messages have no retry** — Minor · fixed by `slice-33-chat-ui-hardening` · found by reading

Steps:
1. Trigger a 429 (send 31 messages in a minute) or stop the gateway, then send a message.

- **Actual:** 429, 403, 422 and 500 all show 'Connection lost'. The optimistic user message stays with no failed marker.
- **Expected:** Distinct messages (wait N seconds / service unavailable / network), failed marker and retry.
- **Where:** `frontend/src/app/home/chat/[id]/page.tsx:127`

### B1

**docker compose does not run the real stack** — Blocker · fixed by `slice-34-local-demo-stack` · found by reading

Steps:
1. cp .env.example .env
2. docker compose --profile full up

- **Actual:** mock-hrms and mock-admissions are busybox stubs although the real services exist. rasa-hr and rasa-admissions run the rasa/rasa image with no trained model instead of their services. rasa-admissions listens on 5007 while compose maps 5007:5005 and the gateway calls :5005. MOCK_HRMS_URL / MOCK_ADMISSIONS_URL are not passed to the packs, and HR/Admissions packs have no depends_on.
- **Expected:** One command brings up postgres, gateway, frontend, the 4 mocks, 3 Rasa servers and 3 action servers, all healthy (slice-27 AC1).
- **Where:** `docker-compose.yml; rasa-admissions/Dockerfile`

### B3

**Database is never migrated or seeded automatically, and seeding is undocumented** — Blocker · fixed by `slice-34-local-demo-stack` · reproduced by running

Steps:
1. Start the stack on an empty database.
2. Ask "check my application status" then give an ID.

- **Actual:** The seed must be run by hand (python -m scripts.seed from backend/); nothing documents it (backend/README.md is empty). The gateway uses create_all at startup while Alembic migrations also exist. Without the seed, many replies say 'Sorry, I couldn't put together a response'. seed.py also logs the full DATABASE_URL including the password.
- **Expected:** Startup runs alembic upgrade head plus an idempotent seed; documented; no secrets logged.
- **Where:** `backend/app/main.py (lifespan create_all); backend/scripts/seed.py:918`

### B4

**Frontend can't reach the API from other laptops (localhost baked into the bundle)** — Blocker · fixed by `slice-34-local-demo-stack` · reproduced by running

Steps:
1. Run the stack on laptop C.
2. From another laptop open http://<C-IP>:3000 and log in.

- **Actual:** The bundle calls http://localhost:8000/api, which is the client's own machine, so login fails with 'Failed to fetch'. There is no /api proxy.
- **Expected:** Frontend proxies /api to the gateway (Next.js rewrites), base URL /api, only port 3000 exposed; works over LAN and over an HTTPS tunnel without mixed-content errors.
- **Where:** `frontend/next.config.mjs; frontend/Dockerfile (ARG); docker-compose.yml; frontend/.env.local`

### N3

**Rate limits break a multi-laptop demo (shared IP behind proxy, single demo account)** — Major · fixed by `slice-34-local-demo-stack` · reproduced by running

Steps:
1. Log in from 4 laptops through one proxy/tunnel within a minute.
2. Have two presenters chat as emp1 at the same time.

- **Actual:** The login limit (10/min) is keyed by client IP, and behind a proxy/tunnel every laptop shares one IP. mock-auth has only one employee account, so all presenters share its 30 chats/min budget (429 hit during the audit).
- **Expected:** One demo login per presenter plus an applicant account (aligned with HRMS/ITSM seeds); limits keyed by the forwarded client IP behind the trusted proxy, or per user.
- **Where:** `backend/app/middleware.py:37-50; mock-auth-service/app/seed_data.py`

### N4

**Docs describe the dropped cloud deployment and an unstarted project** — Minor · fixed by `slice-34-local-demo-stack` · found by reading

Steps:
1. Read README.md, docs/overview.md, docs/ADD.md, the sprint docs, slices 29/30 and .env.example.

- **Actual:** README says 'Implementation has not started' and lists services as stubs; backend/README.md is empty; several docs describe OCI/Cloudflare/Vercel/Neon deployment; AGENTS.md and the slice docs reference docs/vario-overview.md, which doesn't exist (the file is docs/overview.md).
- **Expected:** README documents the local run, ports and accounts; cloud references are marked superseded by the local-demo ADR; broken references fixed.
- **Where:** `README.md; backend/README.md; AGENTS.md; docs/`

### B6

**HR ignores the logged-in employee: balance loops and leave submission always fails** — Blocker · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. Log in as emp1@org.example.com (EMP-1001), open an HR conversation.
2. Send "what is my leave balance?" and reply "EMP-1001".
3. Start a leave request, answer every step, confirm.

- **Actual:** The bot asks for an employee ID; replying 'EMP-1001' classifies as nlu_fallback 0.25, giving a clarification loop. Leave submission ends with 'Unable to submit leave request: employee ID not found'. The gateway's auth_context is dropped (ConverseRequest has no such field) and the sender is a UUID.
- **Expected:** Balance and submission use the logged-in employee from trusted message metadata (ADR-006) without asking.
- **Where:** `rasa-hr/server.py:180, 240, 314`

### B7

**Every leave-request question shows 'Sorry, I couldn't put together a response'** — Blocker · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. HR: send "I want to apply for leave" and answer each prompt.

- **Actual:** The prompts for leave type, start date, end date and reason display the fallback text. Template submit_leave_slot_prompt has no variants and the pack returns no text; talk mode would speak the fallback.
- **Expected:** Each step asks its question (Rasa form utter_ask responses or a seeded template per slot).
- **Where:** `backend/scripts/seed.py:268-284; rasa-hr/actions/actions.py:200, 214, 243, 288`

### B2a

**HR pack imports backend code and silently serves hardcoded data when that fails** — Blocker · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. Run rasa-hr from its own Docker image (no backend/ folder), or stop mock-hrms.
2. Ask for a leave balance or submit leave.

- **Actual:** rasa-hr imports HRMSAdapter from ../../backend via sys.path. In a container the import fails, so balance answers come from hardcoded OFFLINE_EMPLOYEES and submission always says 'service unavailable'. HRMS outages are also hidden by serving the offline data as live (EMP-2001 shows 20 days; HRMS has 27).
- **Expected:** The adapter lives in the HR action server and calls mock-hrms via MOCK_HRMS_URL; an outage gives a clear 'HR system unavailable' reply; no hardcoded employee data.
- **Where:** `rasa-hr/actions/actions.py:7-38, 569`

### M1a

**A second leave request reuses the previous request's dates and reason** — Major · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. Complete one leave request.
2. Send "I want to apply for sick leave".

- **Actual:** It jumps straight to 'Ready to submit? sick leave, <old dates>. Reason: <old reason>'; confirming files an overlapping duplicate and deducts the balance twice. A balance check also presets leave_type=annual, so a later request never asks for the type.
- **Expected:** Form slots reset after submit or cancel; a balance check doesn't set leave_type.
- **Where:** `rasa-hr/actions/actions.py:366-377, 534`

### M2a

**Any user can read another employee's leave balance and file leave as them** — Major · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. As EMP-1001 send "leave balance for EMP-1042".
2. Then "apply for leave", fill the form, confirm.

- **Actual:** Returns Jane Smith's (EMP-1042) balance. EMP-1042 stays in the session, so the request is filed for EMP-1042 (LEAVE-2032). The audit details don't record the target employee.
- **Expected:** HR data and submissions only for the logged-in employee; IDs typed in chat are ignored for these intents; audit records the employee.
- **Where:** `rasa-hr/server.py:300-320; rasa-hr/actions/actions.py:381-390`

### M3a

**Leave form gets stuck after an off-script reply at the confirmation step** — Major · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. Reach the leave confirmation step.
2. Reply "hmm wait".
3. Then send "apply for leave" or "cancel leave request".

- **Actual:** 'Something went wrong… start over', with confirmation_pending left True; every later message gives the same error and only a new conversation escapes. Mid-form, any text (e.g. "what's my balance?") is captured as the slot value.
- **Expected:** Unrecognised replies re-ask; cancel/stop exit at any step; other intents can interrupt the form.
- **Where:** `rasa-hr/actions/actions.py:404-411; rasa-hr/server.py:236-240, 344`

### M4a

**Off-topic policy questions get the leave policy at 0.9 confidence** — Major · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. Send "what is the travel reimbursement policy?", "dress code policy" or "rules".

- **Actual:** ask_policy_faq with the generic leave-policy answer at 0.9 confidence; no clarification (slice-16 AC3).
- **Expected:** Out-of-scope or low-confidence questions get a clarification ('I can help with leave and WFH policies').
- **Where:** `rasa-hr/server.py:153-156`

### M5a

**HR replies with 'Intent greet acknowledged' debug text** — Major · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. HR: send "hi" or "bye".

- **Actual:** 'Intent 'greet' acknowledged.' / 'Intent 'goodbye' acknowledged.'
- **Expected:** Proper greeting and goodbye responses.
- **Where:** `rasa-hr/server.py:425-435`

### N5

**Leave form rejects 'annual' and natural-language dates** — Minor · fixed by `slice-35-hr-real-rasa` · reproduced by running

Steps:
1. At the leave-type prompt reply "annual".
2. At the start-date prompt reply "next monday".

- **Actual:** 'annual' is silently re-prompted although the classifier and HRMS accept it (audit records 'annual', HRMS stores 'earned'). Only YYYY-MM-DD dates are accepted.
- **Expected:** Leave types consistent across NLU, form validation and HRMS; common date formats accepted, or the prompt states the format.
- **Where:** `rasa-hr/server.py:338`

### M4b

**Topic-specific HR FAQ answers are replaced by the generic policy template** — Major · fixed by `slice-36-hr-data-fixes` · reproduced by running

Steps:
1. Ask "what is the maternity policy?", "paternity leave policy", "bereavement leave".

- **Actual:** All get 'Standard leave allotment is 20 annual, 10 sick, and 5 casual days…' because the ask_policy_faq_response variants override the pack's topic-specific text.
- **Expected:** Each topic gets its own answer and stays admin-editable (e.g. one template per topic).
- **Where:** `rasa-hr/server.py:401-410; backend/app/routers/chat.py:114`

### N8

**Leave request status (FR-6) is a stub** — Major · fixed by `slice-36-hr-data-fixes` · reproduced by running

Steps:
1. HR: send "has my leave been approved?".

- **Actual:** 'Intent 'ask_leave_status' acknowledged.'
- **Expected:** Status of the employee's latest (or referenced) leave request from HRMS (FR-6).
- **Where:** `rasa-hr/server.py:425-435`

### M7a

**HR FAQ answers contradict the mock HRMS policy data** — Minor · fixed by `slice-36-hr-data-fixes` · found by reading

Steps:
1. Compare FAQ texts in rasa-hr/server.py and seed.py with mock-hrms /policies.

- **Actual:** WFH 3 vs 2 days/week, maternity 12 vs 26 weeks, bereavement 3 vs 5 days, quotas 20/10/5 vs 8/10/15. FAQ answers never use HRMS get_policy.
- **Expected:** One source of truth for policy facts.
- **Where:** `rasa-hr/server.py; backend/scripts/seed.py; mock-hrms-service/app/seed_data.py`

### N6

**mock-hrms /reset does not restore leave balances** — Minor · fixed by `slice-36-hr-data-fixes` · reproduced by running

Steps:
1. Submit a leave (balance drops).
2. POST /reset.
3. Check the balance and submit again.

- **Actual:** The balance stays reduced but the reference counter resets, so duplicate reference IDs are issued (LEAVE-2032 twice).
- **Expected:** /reset restores all seed data (needed between demo rehearsals).
- **Where:** `mock-hrms-service/app/main.py:11-16; mock-hrms-service/app/seed_data.py:140`

### N7

**mock-hrms accepts invalid leave requests** — Minor · fixed by `slice-36-hr-data-fixes` · reproduced by running

Steps:
1. POST a 90-day leave in 2020 for an employee with 6 days left.

- **Actual:** Accepted; the balance clamps to 0.
- **Expected:** Reject past dates, end-before-start and requests exceeding the balance, with a clear error.
- **Where:** `mock-hrms-service/app/main.py:242-270`

### M3b

**Ticket-ID prompt traps the user; even 'cancel' is rejected** — Major · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. IT: send "check my ticket status".
2. Reply "cancel" or "I want to reset my password".

- **Actual:** 'Please provide a valid ticket ID such as TKT-1234.' for every message that isn't a well-formed ID.
- **Expected:** Cancel and other intents leave the prompt.
- **Where:** `rasa-it/server.py:191-199`

### M4c

**Ticket status questions start a new ticket instead** — Major · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. Send "Is my ticket still open?", "What is the status of the ticket I submitted?" or "is ticket TKT-1234 still open?".

- **Actual:** raise_ticket_form starts: the 'raise' keyword substring check runs before the ID check (2 of the 85 NLU examples misclassify).
- **Expected:** Classified as check_ticket_status.
- **Where:** `rasa-it/server.py:32, 130, 149-152`

### B5c

**IT replies carry the previous ticket's status, so cards show the wrong ticket** — Major · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. Look up IT-1001; raise a ticket and cancel; send "can you check ticket status for me".
2. With mock-itsm stopped: look up IT-1002, then IT-1003.

- **Actual:** session.slots has ticket_id=None, status='In Progress', found=True from the earlier lookup. With ITSM down, IT-1003 shows IT-1002's description and the 'can't reach the ticket system' text is hidden behind the card.
- **Expected:** Each lookup returns only its own result; errors render as errors.
- **Where:** `rasa-it/server.py:430-438`

### M2b

**Password-reset retry limit resets when the flow restarts (unlimited guesses)** — Minor · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. Give 3 wrong security answers.
2. Send "I forgot my password" again and answer correctly.

- **Actual:** The attempt counter resets on restart or cancel, so guessing is unlimited. The reset can also target any employee ID regardless of who is logged in.
- **Expected:** Attempts tracked per employee across restarts (e.g. lockout in mock-itsm); document whether reset is limited to the logged-in employee.
- **Where:** `rasa-it/server.py:328, 480-487`

### N9

**'Ticket created' reply has no ticket ID; 'check my ticket status' reuses the last ID** — Minor · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. Raise a ticket and confirm.
2. Then send "check my ticket status".

- **Actual:** 'Ticket created successfully. Reference ID:' — the ID is only in the card, so the stored message and TTS lack it. 'check my ticket status' with no ID re-queries the previous ticket.
- **Expected:** The ID is in the reply text; with no ID given, the bot asks for one.
- **Where:** `rasa-it/server.py:314, 428`

### N10

**IT pack runs on the wrong Python for Rasa, with unpinned deps and a duplicate adapter** — Minor · fixed by `slice-37-it-real-rasa` · reproduced by running

Steps:
1. pip install -r rasa-it/requirements.txt in a fresh venv; inspect versions.

- **Actual:** rasa-sdk>=3.6.0 resolves to 3.21.x (pulls grpcio/sanic/opentelemetry and forces pydantic 2.13.4). The Dockerfile uses Python 3.11, but Rasa 3.6 needs <=3.10. backend/app/services/itsm_adapter.py is unused at runtime and lacks get_security_question.
- **Expected:** rasa 3.6.20 / rasa-sdk 3.6.x on Python 3.10; a single ITSM adapter.
- **Regression:** the unused backend adapter is removed; HTTP contract tests now cover the single runtime adapter in `rasa-it/tests/test_itsm_adapter.py`.
- **Where:** `rasa-it/requirements.txt; rasa-it/Dockerfile; backend/app/services/itsm_adapter.py`

### M7b

**Bot asks for TKT-1234 but every ticket ID is IT-10xx** — Major · fixed by `slice-38-it-data-and-ci` · reproduced by running

Steps:
1. Follow the bot's example: "status of ticket TKT-1001".

- **Actual:** Not found. Seeded and created tickets are IT-1001…IT-1004.
- **Expected:** One ticket ID format across mock-itsm, prompts, NLU examples and regex, seed and specs.
- **Where:** `rasa-it/server.py prompts; mock-itsm-service/app/seed_data.py:6-8`

### M7c

**IT and Admissions admin logins don't exist in mock-ITSM, so ticket creation loops** — Major · fixed by `slice-38-it-data-and-ci` · reproduced by running

Steps:
1. Log in as it@org.example.com, raise a ticket, press Confirm.

- **Actual:** 'Employee 'EMP-3001' was not found..' and the flow stays at confirm. The UI re-draws the same Confirm card with no error, so the user loops. EMP-4001 behaves the same.
- **Expected:** Every mock-auth login (including the new demo accounts from slice-34) exists in mock-ITSM with documented security Q/A; rejection reasons are shown.
- **Where:** `mock-itsm-service/app/seed_data.py:11-15`

### N11

**CI gaps: mock-service tests never run, 9 IT tests silently skipped, no Rasa validation** — Minor · fixed by `slice-38-it-data-and-ci` · reproduced by running

Steps:
1. Read .github/workflows/ci.yml; run rasa-it tests with its requirements.

- **Actual:** mock-hrms, mock-itsm and mock-admissions tests are never run. The rasa-it async tests are skipped because there's no pytest-asyncio ('21 passed, 9 skipped'). There's no rasa data validate step, and the 'when present' IT job is stale.
- **Expected:** All service tests run with 0 skipped; each pack validates its Rasa data.
- **Where:** `.github/workflows/ci.yml:96-202`

### B2b

**Admissions pack never calls mock-admissions; answers are hardcoded (FR-16 broken)** — Blocker · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. Run rasa-admissions with its own requirements.txt.
2. Ask any status/checklist/fee question.
3. PUT /calendar on mock-admissions to change a fee and ask again.

- **Actual:** The adapter import from ../backend fails (pydantic_settings missing; backend/ not in the image), so HAS_ADAPTER=False and answers come from OFFLINE_* dicts. mock-admissions received 0 requests in the audit. The offline data differs from the mock (APP-1002/1003), calendar edits never show, and OFFLINE_CALENDAR violates slice-26. The AC-3 test edits OFFLINE_CALENDAR, so it can't fail.
- **Expected:** The adapter lives in the Admissions action server; every answer comes from mock-admissions; calendar edits are reflected.
- **Where:** `rasa-admissions/actions/actions.py:31-44, 439; rasa-admissions/tests/test_admissions_rasa.py:407`

### M3c

**A pending Admissions prompt swallows the next message** — Major · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. Send "check my application status", then "actually what is the MBA tuition fee?".
2. Or after 'Which program…?' send "what is the status of APP-1001".

- **Actual:** 'Application ACTUALLY WHAT IS THE MBA TUITION FEE? was not found'; the status question is stored as the program.
- **Expected:** Other intents interrupt the prompt.
- **Where:** `rasa-admissions/server.py:221-232`

### M1b

**Admissions reuses stale application IDs and programs** — Major · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. Ask the status of APP-9999, then "check application status".
2. Or ask about APP-1003, then "what's the status of my application app 1001?".

- **Actual:** Re-reports the previous ID without asking / answers for APP-1003. Checklist reuses the previous program without asking.
- **Expected:** Ask for an ID or program unless it's given in this request.
- **Where:** `rasa-admissions/server.py:248, 283`

### M5b

**Admissions replies with 'Intent greet acknowledged' debug text** — Major · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. Admissions: send "hi" or "bye".

- **Actual:** 'Intent 'greet' acknowledged.' (utter_greet exists but is unused).
- **Expected:** Proper greeting and goodbye responses.
- **Where:** `rasa-admissions/server.py:363-372`

### M6b

**Admissions reports 'not found' when the service is actually down** — Minor · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. Stop mock-admissions; ask the status of APP-1005.

- **Actual:** 'Application APP-1005 was not found.'
- **Expected:** 'The admissions system is unavailable, please try again later.'
- **Where:** `rasa-admissions/actions/actions.py`

### N13

**Admissions misclassifies common follow-up questions** — Minor · fixed by `slice-39-adm-real-rasa` · reproduced by running

Steps:
1. After a fee answer send "and for btech?".
2. Send "any update on fees?" and "what are the dates?".

- **Actual:** 'and for btech?' → checklist; 'any update on fees?' → asks for an application ID; 'what are the dates?' → nlu_fallback 0.42.
- **Expected:** Fee/deadline follow-ups classified correctly.
- **Where:** `rasa-admissions/server.py`

### N14

**Admissions card components are dead code duplicated in the chat page** — Trivial · fixed by `slice-39-adm-real-rasa` · found by reading

Steps:
1. Search for AdmissionsStatusCard / AdmissionsNotFoundCard usages.

- **Actual:** AdmissionsStatusCard, AdmissionsNotFoundCard and createAdmissions*Message are unused; page.tsx re-implements the same rendering.
- **Expected:** The chat page renders admissions cards through these components (coordinate with slice-33), or they are removed.
- **Where:** `frontend/src/components/chat/AdmissionsStatusCard.tsx; frontend/src/app/home/chat/[id]/page.tsx`

### B8

**Admin conversation-logs page expects field names the backend doesn't send** — Blocker · fixed by `slice-40-admin-console-fixes` · reproduced by running

Steps:
1. Log in as an admin, open Conversation Logs, click a row.

- **Actual:** The frontend uses conversation_id/message_id/sender_type/user_id; the backend and api-contract use id/sender. Every row expands, the transcript fetch hits /admin/conversations/undefined/messages (404), and all messages render as bot. The tests use the frontend's invented shape, so they pass.
- **Expected:** Types match the backend schemas; tests use contract-shaped fixtures.
- **Where:** `frontend/src/lib/api.ts:156-185; frontend/src/app/admin/conversation-logs/page.tsx; frontend/__tests__/admin-conversation-logs.test.tsx:29, 66`

### M9a

**Saving an intent wipes its stored reply variants** — Major · fixed by `slice-40-admin-console-fixes` · reproduced by running

Steps:
1. As hr@ open ask_wfh_policy, add one training phrase, save.

- **Actual:** The editor always sends the template update; the backend regenerates variants via the passthrough rephraser, so the 5 seeded variants become 1. Inline variant edits then 404 (stale IDs).
- **Expected:** Template only updated when changed; variants regenerate only when base_text changes.
- **Where:** `frontend/src/components/admin/IntentEditor.tsx:190-204; backend/app/routers/admin_crud.py:355-359`

### M9b

**Seeded reply variants can't be deleted** — Minor · fixed by `slice-40-admin-console-fixes` · reproduced by running

Steps:
1. As hr@ try to delete any seeded variant of ask_wfh_policy_response.

- **Actual:** 400 'Cannot delete the original base_text variant' — seed inserts every variant with the default position 0.
- **Expected:** Seed sets position 0 only for the original and 1..n for the rest.
- **Where:** `backend/scripts/seed.py (all variant inserts); backend/app/routers/admin_crud.py delete_variant`

### M9c

**Admin configuration changes are not audit-logged** — Minor · fixed by `slice-40-admin-console-fixes` · reproduced by running

Steps:
1. As hr@ create an FAQ and edit a template; open the audit log.

- **Actual:** 0 entries: admin_crud writes no audit events. The audit filter options intent_created/intent_updated/template_edited can never match, and password_reset_initiated is missing from the dropdown.
- **Expected:** Intent create/update/delete and template/variant edits are recorded with role_pack; the dropdown matches the recorded types.
- **Where:** `backend/app/routers/admin_crud.py; frontend/src/app/admin/audit-log/page.tsx`

### N15

**Conversation-log filters fire on every keystroke; the 'to' date excludes that day** — Minor · fixed by `slice-40-admin-console-fixes` · found by reading

Steps:
1. Type an email into the user filter; set 'to' = today.

- **Actual:** Each keystroke sends a request (can hit the 30/min admin limit, giving 429); the Apply button is redundant; 'to'=YYYY-MM-DD is parsed as midnight, so that day is excluded; the actor filter needs a raw UUID despite saying 'Search by user'.
- **Expected:** Apply/debounced filtering, inclusive 'to' date, search by name or email.
- **Where:** `frontend/src/app/admin/conversation-logs/page.tsx:68-97; backend/app/routers/admin.py:62`

### N16

**'Retraining' nav item links to a page that doesn't exist** — Trivial · fixed by `slice-40-admin-console-fixes` · reproduced by running

Steps:
1. Log in as an admin and click Retraining.

- **Actual:** /admin/retraining returns 404.
- **Expected:** Hidden until slice-10 ships, then linked to the retraining page.
- **Where:** `frontend/src/app/admin/layout.tsx:16`

### N12

**Admin-created FAQ intents are never answered (no retrain path)** — Major · fixed by `slice-10-retraining` · reproduced by running

Steps:
1. As hr@ create FAQ intent ask_dress_code with phrases "what is the dress code?" and a response.
2. As an employee ask "what is the dress code?".

- **Actual:** nlu_fallback. Nothing reads intents from the DB and there is no retrain path, so FR-18 'change is live' only holds for editing existing reply text.
- **Expected:** After retraining (slice-10, now on real Rasa) the new FAQ is classified and answered from its template.
- **Where:** `backend/app/routers/admin_crud.py; role packs`
