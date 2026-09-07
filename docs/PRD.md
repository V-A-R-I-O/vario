# PRD — V.A.R.I.O (Voice Adaptive Role & Intent Orchestrator)

## Goal
Build a role-specific, context-aware voice and text assistant framework that helps organizations automate repetitive, low-complexity queries and transactional requests. The solution will provide a single, reusable core engine with pluggable "role packs" (HR, IT Support, Admissions) to handle departmental workflows, saving staff time and eliminating the need to build separate chatbots from scratch.

## Users
- **End Users:** Employees (for HR and IT Support queries) and Students/Applicants (for Admissions queries).
- **Role Administrators:** Department staff (HR, IT, Admissions) who manage the intents, FAQs, and workflows for their specific domain.
- **System Administrators:** The development team deploying, monitoring, and extending the core engine and integration adapters.

## Core features
- **Multi-Turn Intent Recognition:** Core NLU engine that classifies role/intent, maintains context across multiple turns, and supports fallback/clarification for low-confidence queries.
- **Text & Voice Interaction:** A web-based React interface supporting both typed chat and spoken input/output via the Web Speech API.
- **HR Self-Service (Role Pack):** Check leave balance/status, ask policy FAQs, and submit leave requests through a guided conversational flow.
- **IT Support Self-Service (Role Pack):** Create IT support tickets, check ticket status, and perform a guided password-reset flow (preventing duplicate ticket creation).
- **Admissions Self-Service (Role Pack):** Check application status, access document checklists, and ask fee/deadline-related questions from a configurable calendar.
- **Admin Configuration Console:** A JWT-authenticated web interface allowing Role Administrators to add, edit, or remove intents/FAQs and view workflow logs for their specific role.
- **Integration Adapter Layer:** A common interface abstracting backend systems, connected to mock FastAPI services simulating HRMS, ITSM, and Admissions systems.

## Out of scope
- **Real enterprise integrations:** Integration with a live, real-world HRMS, ITSM, or Admissions system is excluded (v1 uses mock APIs only).
- **Multi-language support:** Support for languages other than English is excluded in v1.
- **Native mobile app:** A native iOS/Android application is excluded (the web UI will be mobile-responsive).
- **Advanced analytics:** Complex BI dashboards are excluded beyond a basic log of conversations and workflow actions in the admin console.
- **Proactive notifications:** Push notifications for status changes (e.g., ticket resolved) are excluded; the system only responds to user-initiated queries.
- **SSO:** Single-sign-on integration for end-user authentication is excluded in v1.

## Success criteria
- **Performance:** 95% of queries (excluding artificial mock API delays) return a response within 2 seconds.
- **Scalability:** The system supports at least 20 concurrent user sessions during a demo without noticeable response-time degradation.
- **Extensibility:** Adding a new role pack requires configuration changes only (no core-engine code changes) and can be achieved in under one developer-day.
- **Functional Completeness:** Every functional requirement defined (e.g., leave submission, ticket creation, password reset) can be completed successfully via the conversational interface.

## Open questions
- **NLU Selection:** Should the primary intent recognition be built using Rasa Open Source or a custom spaCy-based classifier to best balance accuracy and development speed?
- **Mock Identity Verification:** What specific mechanism will be used to mock the "identity verification" step during the IT password-reset flow?
- **Data Schema:** How exactly will the PostgreSQL database schema be designed to seamlessly isolate configuration and logs across different role packs while maintaining a shared session table?