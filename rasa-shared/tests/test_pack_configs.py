"""Each role pack's Rasa config must load through Rasa's own readers (needs Rasa).

Rasa expands only plain ${VAR} references: `${VAR:-default}` makes `rasa run`
fail, and a quoted "${VAR}" is sent literally. Both shipped once; this test
loads every pack's endpoints.yml exactly as `rasa run` would.
"""
from pathlib import Path

import pytest
from rasa.core.utils import AvailableEndpoints

from tests.conftest import RASA_SHARED

REPO = RASA_SHARED.parent
PACKS = ["rasa-hr", "rasa-it"]
ENV = {
    "ACTION_ENDPOINT_URL": "http://actions.test:5055/webhook",
    "POSTGRES_HOST": "postgres.test",
    "POSTGRES_DB": "rasa_pack_test",
    "POSTGRES_USER": "vario_test",
    "POSTGRES_PASSWORD": "secret_test",
}


@pytest.mark.parametrize("pack", PACKS)
def test_endpoints_expand_every_variable(pack, monkeypatch):
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    endpoints = AvailableEndpoints.read_endpoints(str(REPO / pack / "endpoints.yml"))

    assert endpoints.action.url == ENV["ACTION_ENDPOINT_URL"]
    store = endpoints.tracker_store
    assert store.type == "vario_rasa.tracker_store.RedactingSQLTrackerStore"
    assert store.url == ENV["POSTGRES_HOST"]
    assert store.kwargs["db"] == ENV["POSTGRES_DB"]
    assert store.kwargs["username"] == ENV["POSTGRES_USER"]
    assert store.kwargs["password"] == ENV["POSTGRES_PASSWORD"]


@pytest.mark.parametrize("pack", PACKS)
def test_credentials_register_the_vario_channel(pack):
    text = Path(REPO / pack / "credentials.yml").read_text(encoding="utf-8")
    assert "vario_rasa.channel.VarioInputChannel" in text
