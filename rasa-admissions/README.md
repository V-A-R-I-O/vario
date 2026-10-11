# VARIO — Rasa Admissions Role Pack

NLU and dialogue orchestration engine for the Admissions Role Pack. Runs at `RASA_ADMISSIONS_URL` (`http://localhost:5007`).

## Core Responsibilities

- **Intent Recognition:** Identifies user intentions (`check_application_status`, `get_document_checklist`, `ask_fee_deadline`).
- **Entity Extraction:** Extracts `application_id` (e.g., `APP-1001`) and degree `program`.
- **Dialogue Policy & Fallback:** `FallbackClassifier` triggers graceful fallback prompts when confidence < 0.4.
- **VARIO Converse Contract:** Implements `POST /webhooks/vario/converse` per `docs/decisions/ADR-002-rasa-chat-contract.md`.

## Directory Structure

```
rasa-admissions/
├── config.yml           # Pipeline and policy configuration
├── domain.yml           # Intents, entities, slots, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations
└── channels/
    └── vario.py         # ADR-002 converse webhook implementation
```
