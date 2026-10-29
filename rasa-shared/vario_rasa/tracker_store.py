"""SQL tracker store that never persists sensitive user input (ADR-006 §6).

Configure it in a role pack's endpoints.yml:

    tracker_store:
      type: vario_rasa.tracker_store.RedactingSQLTrackerStore
      dialect: postgresql
      url: postgres
      db: rasa_it
      username: ${POSTGRES_USER}
      password: ${POSTGRES_PASSWORD}

A user turn sent with `metadata.sensitive = true` (e.g. a security answer) is
saved with its text replaced and entities dropped, and any slot set to that
text during the same turn is redacted too. Actions still see the real text
while the turn runs; only what is written to the database is scrubbed.
"""
from rasa.core.tracker_store import SQLTrackerStore
from rasa.shared.core.events import SlotSet, UserUttered
from rasa.shared.core.trackers import DialogueStateTracker

from vario_rasa.contract import REDACTED_TEXT


def redact_sensitive_turns(tracker: DialogueStateTracker) -> None:
    """Scrub sensitive user turns (and slots filled from them) in place."""
    secret = None
    for event in tracker.events:
        if isinstance(event, UserUttered):
            secret = None
            if (event.metadata or {}).get("sensitive") and event.text != REDACTED_TEXT:
                secret = event.text
                event.text = REDACTED_TEXT
                event.entities = []
                event.parse_data["text"] = REDACTED_TEXT
                event.parse_data["entities"] = []
        elif secret and isinstance(event, SlotSet) and isinstance(event.value, str):
            if secret.strip() and secret.strip() in event.value:
                event.value = REDACTED_TEXT


class RedactingSQLTrackerStore(SQLTrackerStore):
    """`SQLTrackerStore` that redacts sensitive turns before every save."""

    async def save(self, tracker: DialogueStateTracker) -> None:
        redact_sensitive_turns(tracker)
        await super().save(tracker)
