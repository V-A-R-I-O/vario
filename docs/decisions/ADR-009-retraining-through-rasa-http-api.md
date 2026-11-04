# ADR 009: Retraining Through Rasa's HTTP API

**Date:** 2026-11-04
**Status:** Accepted
**Slice:** slice-10-retraining (SCRUM-31)

## Context

All three role packs now run real Rasa 3.6.20. The first retraining worker:
- posted a multipart upload that Rasa 3.6 does not accept;
- then called `/model/reload`, an endpoint that doesn't exist;
- sent IT to a `/internal/retrain` endpoint that only the old keyword runtime had.

It also **replaced** each intent's NLU examples with the database phrases. That dropped the entity annotations the forms depend on, for example `apply for [sick](leave_type) leave`.

## Decision

- **Train:** the gateway sends one YAML document to the pack's own Rasa server: `POST /model/train?save_to_default_model_directory=true`. The document holds the pack's `config.yml`, `domain.yml`, `data/nlu.yml`, `data/rules.yml` and `data/stories.yml`, merged with the admin console's data.
- **Load:** the gateway then calls `PUT /model` with `models/<filename>`, using the filename Rasa returns in the `filename` header. Rasa trains in a worker thread, so chat keeps working while it trains.
- **Merge rules:**
  - The pack files are the base. Database phrases are appended to the matching intent. A phrase that matches an existing example with its annotations stripped is not added again.
  - A static FAQ the domain doesn't know yet gets three things: the intent, an `utter_<name>` response carrying `custom.vario.template_key: <name>_response` (so the gateway renders the admin-editable template and its variants), and a rule.
  - A database intent that isn't in the domain and has no answer is skipped with a warning.
- **Auth:** `RETRAINING_INTERNAL_TOKEN` is sent as Rasa's `?token=`. Set the same value as each server's `rasa run --auth-token`. Leave it empty only when the servers run without a token. The chat webhook is not affected by the token.
- **Pack files:** read from `ROLE_PACKS_DIR/<pack>`, as mounted by Compose, or from `ROLE_PACKS_DIR/rasa-<pack>` when `ROLE_PACKS_DIR` points at the repo for a native run.

## Consequences

- An admin-created FAQ is answered after a retrain, with no code change or redeploy (FR-3).
- Deleting a phrase in the console removes it only if it came from the database. A phrase that lives in a pack's `nlu.yml` stays until a developer removes it there.
- The retrained model is saved in the Rasa server's `models/` directory. It survives a restart only if that directory is on a volume (slice-34).
