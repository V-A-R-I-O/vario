# PRD — V.A.R.I.O (Voice Adaptive Role & Intent Orchestrator)

## Goal
Build a role-specific, context-aware voice and text assistant framework that helps organizations automate repetitive, low-complexity queries and transactional requests. The solution will provide a single, reusable core engine with pluggable "role packs" (HR, IT Support, Admissions) to handle departmental workflows, saving staff time and eliminating the need to build separate chatbots from scratch.

## Users
- **End Users:** Employees (for HR and IT Support queries) and Students/Applicants (for Admissions queries). Authenticated via the organization's existing identity provider.
- **Role Administrators:** Department staff (HR, IT, Admissions) who manage the intents, FAQs, and workflows for their specific domain.
- **System Administrators:** The development team deploying, monitoring, and extending the core engine and integration adapters.

## Core features
- **Multi-Turn Intent Recognition:** Core NLU engine that classifies role/intent, maintains context across multiple turns, and supports fallback/clarification for low-confidence queries.
- **Text & Voice Interaction:** A web-based React interface supporting both typed chat and spoken input/output via the Web Speech API.
- **HR Self-Service (Role Pack):** Check leave balance/status, ask policy FAQs, and submit leave requests through a guided conversational flow.
- **IT Support Self-Service (Role Pack):** Create IT support tickets, check ticket status, and perform a guided password-reset flow with mock identity verification (preventing duplicate ticket creation).
- **Admissions Self-Service (Role Pack):** Check application status, access document checklists, and ask fee/deadline-related questions from a configurable calendar.
- **Admin Configuration Console:** A JWT-authenticated web interface allowing Role Administrators to add, edit, or remove intents/FAQs, generate training phrase variants via a "Generate Similar" feature, manage response template variants, and view workflow logs for their specific role.
- **Integration Adapter Layer:** A common interface abstracting backend systems, connected to mock FastAPI services simulating Auth, HRMS, ITSM, and Admissions systems. All adapters (Auth, HRMS, ITSM, Admissions) follow the same pattern — mock today, swappable to real systems later.
- **Delegated Authentication:** VARIO does not manage user accounts. Authentication is delegated to the organization's existing identity provider via an Auth Adapter. A Mock Auth Service (pre-seeded with test users) is provided for development and demo. VARIO issues its own JWT with an embedded role claim after the org validates the user.

## Out of scope
- **Real enterprise integrations:** Integration with a live, real-world HRMS, ITSM, or Admissions system is excluded (v1 uses mock APIs only).
- **Multi-language support:** Support for languages other than English is excluded in v1.
- **Native mobile app:** A native iOS/Android application is excluded (the web UI will be mobile-responsive).
- **Advanced analytics:** Complex BI dashboards are excluded beyond a basic log of conversations and workflow actions in the admin console.
- **Proactive notifications:** Push notifications for status changes (e.g., ticket resolved) are excluded; the system only responds to user-initiated queries.
- **User management:** VARIO does not manage user accounts, registration, or password resets — these are the responsibility of the integrating organization's identity system.

## Success criteria
- **Performance:** 95% of queries (excluding artificial mock API delays) return a response within 2 seconds.
- **Scalability:** The system supports at least 20 concurrent user sessions during a demo without noticeable response-time degradation.
- **Extensibility:** Adding a new role pack requires configuration changes only (no core-engine code changes) and can be achieved in under one developer-day.
- **Functional Completeness:** Every functional requirement defined (e.g., leave submission, ticket creation, password reset) can be completed successfully via the conversational interface.

## Open questions
- **Mock Identity Verification:** Resolved — the IT password-reset flow uses employee ID + security question checked against Mock ITSM data to simulate identity verification before triggering a mock password reset.

## User Stories

### End Users (Employees, Students)
- **US-1:** As an employee, I want to ask for my leave balance using natural language so I don't have to navigate through the complex HRMS portal.
- **US-2:** As an employee with an IT issue, I want to describe my problem to the bot and have it automatically create a support ticket for me.
- **US-3:** As an employee locked out of my account, I want to verify my identity via a security question and have the bot reset my password immediately.
- **US-4:** As an applicant, I want to ask about application deadlines so I can ensure my documents are submitted on time.
- **US-5:** As a user on the go, I want to use my microphone to speak to the bot and hear its response spoken back to me.

### Role Administrators (HR, IT, Admissions Staff)
- **US-6 (Static FAQs):** As an admin, I want to create a new FAQ from scratch (e.g., "What is the WFH policy?") by entering training phrases and a static text response, so I can answer common policy questions without needing a developer.
- **US-7 (Dynamic Workflows):** As an admin, I want to edit the response text for complex workflows (e.g., Ticket Status) using read-only variable badges (like `{ticket_id}` and `{status}`) provided by the developers, so I can customize the bot's tone without breaking the underlying data integration.
- **US-8:** As an admin creating training phrases, I want to click a "Generate Similar" button to have the AI suggest 8 new phrase variations, so I don't have to manually brainstorm every possible way a user might ask a question.
- **US-9:** As an admin writing a response template, I want the system to automatically generate 4 paraphrased variants of my answer, so the bot sounds natural and less robotic when answering the same question multiple times.
- **US-10:** As an admin, I want to view a log of all past conversations handled by my department's bot, so I can identify areas where the bot misunderstood users and improve its training phrases.