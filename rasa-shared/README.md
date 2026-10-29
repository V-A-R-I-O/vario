# rasa-shared — VARIO code shared by the Rasa role packs

The single copy of the platform pieces every role pack uses. The contract is in
[`docs/decisions/ADR-006-rasa-contract-v2.md`](../docs/decisions/ADR-006-rasa-contract-v2.md).

| Path | What it is | Needs Rasa? |
|---|---|---|
| `vario_rasa/contract.py` | `vario_payload()` for actions, `build_converse_response()`, `CARD_TYPES` | No — safe to import in an action server |
| `vario_rasa/channel.py` | `VarioInputChannel` — serves `POST /webhooks/vario/converse` | Yes |
| `vario_rasa/tracker_store.py` | `RedactingSQLTrackerStore` — keeps secrets out of the tracker DB | Yes |
| `contract/*.json` | Frozen request/response examples to test against | — |

## Using it in a role pack

`credentials.yml`:

```yaml
vario_rasa.channel.VarioInputChannel: {}
```

`endpoints.yml`:

```yaml
tracker_store:
  type: vario_rasa.tracker_store.RedactingSQLTrackerStore
  dialect: postgresql
  url: postgres
  db: rasa_hr            # rasa_it / rasa_admissions
  username: ${POSTGRES_USER}
  password: ${POSTGRES_PASSWORD}
```

In an action, send the VARIO fields as custom JSON:

```python
from vario_rasa.contract import vario_payload

dispatcher.utter_message(text="You have 22 days of leave remaining.")
dispatcher.utter_message(json_message=vario_payload(
    template_key="check_leave_balance_response",
    slots={"total": 22},
    card={"type": "data_card", "title": "Your leave balance",
          "rows": [{"label": "Total", "value": "22 days"}]},
))
```

When asking for a secret (e.g. a security answer), send `vario_payload(sensitive_next_input=True)`
with the question, verify the answer in `validate_<slot>`, and never keep it in a slot.

**Making the module importable:**
- **Docker:** mount `rasa-shared/vario_rasa` at `/app/vario_rasa` (slice-34).
- **Native:** set `PYTHONPATH` to this folder before `rasa run` (macOS/Linux shown first, then Windows PowerShell):

```bash
PYTHONPATH=../rasa-shared rasa run --enable-api            # macOS / Linux
$env:PYTHONPATH="..\rasa-shared"; rasa run --enable-api    # Windows PowerShell
```

## Tests

Rasa 3.6 needs Python 3.8–3.10.

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

- `test_contract.py` — pure Python, runs in under a second.
- `test_tracker_store.py` — redaction unit tests.
- `test_rasa_integration.py` — trains `tests/fixture_bot` and starts a real `rasa run` with the channel and redacting tracker store (about a minute).
