# Research — V.A.R.I.O (Voice Adaptive Role & Intent Orchestrator)

## The problem
Organizations (such as universities and companies) field a large volume of repetitive, low-complexity queries and transactional requests directed at departments like HR, IT Support, and Admissions. This consumes valuable staff time that could be spent on higher-value work, while users face delays waiting for responses to well-defined, repeatable issues. Existing chatbot solutions are typically built as one-off, single-domain bots, meaning organizations duplicate engineering effort for each department and struggle to introduce new departmental assistants quickly.

## Who has this problem
- **End Users (Employees / Students / Applicants):** They experience delays getting simple answers (e.g., leave balances, IT ticket status, admissions application status).
- **Role Administrators (HR / IT / Admissions Staff):** They spend too much time answering repetitive questions instead of focusing on complex tasks.
- **System Administrators / Organizations:** They face the burden of building, maintaining, and scaling separate, siloed chatbot systems for every department.

## Why now / why you
This project is being developed by Team PIPELINE as part of the Software Engineering Jackfruit Mini-Project at PES University. The goal is to build a modern, scalable, and reusable solution using Agile SDLC practices, demonstrating how a single engine can serve multiple organizational roles efficiently.

## What exists already
Existing solutions are usually single-purpose chatbots. When an organization wants a bot for HR and another for IT, they often build two separate systems with duplicated core logic (NLU, routing, session management). They fail to provide a shared conversational "brain" that can simply be configured with different vocabularies and workflows for different departments.

## Rough shape of the solution
A single, reusable assistant framework whose core conversational engine is shared across roles, while each role's specific knowledge and workflows remain independently configurable via pluggable "role packs". It will support both text and voice interactions and use a swappable integration-adapter layer to connect with departmental tools (HRMS, ITSM, Admissions software).

## Open questions

> [!NOTE]
> This is an early discovery doc. Both questions below have since been **resolved** — kept here for historical context. See `docs/ADD.md` for the current decisions.

- ~~Which NLU framework (Rasa Open Source vs. spaCy-based classifier) will ultimately be chosen and provide the best accuracy for the project's scope?~~ **Resolved:** Rasa Open Source, run as 3 isolated instances (one per role pack). See `docs/ADD.md`.
- ~~How exactly will the mock internal-tool APIs (HRMS, ITSM, Admissions) be structured to ensure a seamless transition to real enterprise systems in the future?~~ **Resolved:** behind a common Integration Adapter interface (one adapter per system), with mock FastAPI services in dev — swappable to real backends without touching Rasa or the router. See `docs/ADD.md` and `docs/api-contract.md`.