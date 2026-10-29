"""Slice 10 IT runtime tests: authentication and durable example reload."""
import json

from fastapi.testclient import TestClient

import server


def test_internal_retraining_requires_configured_token(monkeypatch, tmp_path):
    monkeypatch.setenv("RETRAINING_INTERNAL_TOKEN", "")
    monkeypatch.setenv("RETRAINING_DATA_PATH", str(tmp_path / "training_examples.json"))
    client = TestClient(server.app)

    response = client.post(
        "/internal/retrain",
        json={"examples_by_intent": {"ask_vpn_renewal": ["renew my vpn certificate please"]}},
        headers={"X-Vario-Internal-Token": "dev-retraining-token-change-me"},
    )
    assert response.status_code == 401


def test_internal_retraining_persists_and_reloads_examples(monkeypatch, tmp_path):
    data_path = tmp_path / "training_examples.json"
    monkeypatch.setenv("RETRAINING_INTERNAL_TOKEN", "test-only-secret")
    monkeypatch.setenv("RETRAINING_DATA_PATH", str(data_path))
    client = TestClient(server.app)
    original = dict(server.TRAINING_DATA)

    response = client.post(
        "/internal/retrain",
        json={"examples_by_intent": {"ask_vpn_renewal": ["renew my vpn certificate please"]}},
        headers={"X-Vario-Internal-Token": "test-only-secret"},
    )
    assert response.status_code == 200
    assert json.loads(data_path.read_text(encoding="utf-8"))["ask_vpn_renewal"] == [
        "renew my vpn certificate please"
    ]
    assert server.classify_message("renew my vpn certificate please")[0] == "ask_vpn_renewal"

    # Simulate a fresh process loading the persisted overlay on top of canonical NLU.
    server.TRAINING_DATA = dict(original)
    server.load_persisted_training_examples()
    assert server.classify_message("renew my vpn certificate please")[0] == "ask_vpn_renewal"
