# VARIO — Rasa HR Role Pack

NLU and dialogue orchestration engine for the HR Role Pack. Runs at `RASA_HR_URL` (`http://localhost:5005`).

## Core Responsibilities

- **Intent Recognition:** Identifies user intentions (`check_leave_balance`, `ask_leave_status`, `submit_leave_request`, `ask_policy_faq`).
- **Entity Extraction:** Extracts `employee_id` (e.g., `EMP-1042`) and `leave_type` (e.g., `annual`, `sick`, `casual`).
- **Dialogue Policy & Fallback:** `FallbackClassifier` triggers graceful fallback prompts when confidence < 0.4 (supports FR-2).
- **VARIO Converse Contract:** Implements `POST /webhooks/vario/converse` per `docs/decisions/ADR-002-rasa-chat-contract.md`.
- **Custom Actions:** Provides `action_check_leave_balance` skeleton returning `template_key` + slots shape.

## Directory Structure

```
rasa-hr/
├── config.yml           # Pipeline and policy configuration
├── domain.yml           # Intents, entities, slots, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── server.py            # FastAPI server running ADR-002 converse webhook
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations (action_check_leave_balance)
├── channels/
│   └── vario.py         # ADR-002 converse webhook implementation
└── tests/
    └── test_hr_rasa.py  # Unit and integration tests for HR Rasa service
```
