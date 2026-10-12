# VARIO — Rasa Admissions Role Pack

NLU and dialogue orchestration engine for the Admissions Role Pack. Runs at `RASA_ADMISSIONS_URL` (`http://localhost:5007`).

## Core Responsibilities

- **Intent Recognition:** Identifies user intentions (`check_application_status`, `get_document_checklist`, `ask_fee_deadline`).
- **Entity Extraction:** Extracts `application_id` (e.g., `APP-1001`) and degree `program`.
- **Dialogue Policy & Fallback:** `FallbackClassifier` triggers graceful fallback prompts when confidence < 0.4 or when intent ambiguity is detected (`ambiguity_threshold: 0.1`).
- **Missing Slot Prompts:** When checking application status without providing an ID, requests the application ID rather than assuming a default ID.
- **VARIO Converse Contract:** Implements `POST /webhooks/vario/converse` per `docs/decisions/ADR-002-rasa-chat-contract.md`.

## Runtime Architecture & Slice Scope (Slice 22 vs Slice 29)

- **Local Dev & Testing Runtime (`server.py`):**
  Provides a fast, zero-weight service implementation for local development, pytest test suites, and CI runners without requiring heavy TensorFlow and native C++ compiler wheels on developer host machines. It loads the canonical training data directly from `data/nlu.yml` and emulates the configured Rasa pipeline (`WhitespaceTokenizer`, `CountVectorsFeaturizer`, `DIETClassifier`, and `FallbackClassifier` with `threshold: 0.4` and `ambiguity_threshold: 0.1`).
- **Production Containerized Rasa Engine (Slice 29):**
  The containerized deployment running official Rasa Open Source (`rasa train` / `rasa run --enable-api`) with DIETClassifier neural network model weights is scheduled for Slice 29 (`infra-docker-compose`). All Rasa configuration files (`config.yml`, `domain.yml`, `data/nlu.yml`, `data/rules.yml`, and `data/stories.yml`) adhere strictly to standard Rasa 3.x specifications.

## Directory Structure

```
rasa-admissions/
├── config.yml           # Pipeline and policy configuration (DIET, FallbackClassifier)
├── domain.yml           # Intents, entities, slots, forms, and actions
├── credentials.yml      # Custom channel connector setup
├── endpoints.yml        # Action server endpoint
├── data/
│   ├── nlu.yml          # Training phrases with entity annotations
│   ├── rules.yml        # Dialogue rules
│   └── stories.yml      # Multi-turn stories
├── actions/
│   └── actions.py       # Custom action implementations (ActionCheckApplicationStatus)
├── channels/
│   └── vario.py         # ADR-002 converse webhook implementation for native Rasa
└── server.py            # Local FastAPI runtime implementing ADR-002 converse contract
```

