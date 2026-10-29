"""Tests for the Rasa retraining lifecycle used by every role pack."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services import retraining_service


@pytest.mark.asyncio
async def test_it_retraining_trains_and_reloads_the_real_rasa_server(monkeypatch):
    monkeypatch.setitem(retraining_service.URLS, "it", "http://rasa-it:5006")
    monkeypatch.setattr(
        retraining_service,
        "_prepare_assets",
        lambda pack, rows: "version: \"3.1\"\nintents: []\n",
    )

    train_response = MagicMock()
    train_response.headers = {"filename": "it-model.tar.gz"}
    train_response.raise_for_status = MagicMock()
    activation_response = MagicMock()
    activation_response.raise_for_status = MagicMock()

    client = MagicMock()
    client.post = AsyncMock(return_value=train_response)
    client.put = AsyncMock(return_value=activation_response)
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.retraining_service.httpx.AsyncClient", return_value=context):
        await retraining_service.train(
            "it", [{"name": "ask_vpn_renewal", "examples": ["renew my vpn certificate"]}]
        )

    assert client.post.await_count == 1
    assert client.put.await_count == 1
    first_call = client.post.await_args
    second_call = client.put.await_args
    assert first_call.args[0] == "http://rasa-it:5006/model/train?save_to_default_model_directory=true"
    assert first_call.kwargs["headers"]["Content-Type"] == "application/x-yaml"
    assert "intents:" in first_call.kwargs["content"]
    assert second_call.args[0] == "http://rasa-it:5006/model"
    assert second_call.kwargs["json"] == {"model_file": "models/it-model.tar.gz"}
    assert first_call.kwargs["headers"]["Content-Type"] == "application/x-yaml"


def test_prepare_assets_combines_config_domain_nlu_and_rules(monkeypatch, tmp_path):
    import yaml

    role_pack = tmp_path / "it"
    (role_pack / "data").mkdir(parents=True)
    (role_pack / "config.yml").write_text(
        "recipe: default.v1\nlanguage: en\npipeline: []\npolicies: []\n",
        encoding="utf-8",
    )
    (role_pack / "domain.yml").write_text(
        'version: "3.1"\nintents:\n  - greet\nresponses:\n  utter_greet:\n    - text: Hi\n',
        encoding="utf-8",
    )
    (role_pack / "data" / "nlu.yml").write_text(
        'version: "3.1"\nnlu:\n  - intent: greet\n    examples: |\n      - hi\n',
        encoding="utf-8",
    )
    (role_pack / "data" / "rules.yml").write_text(
        'version: "3.1"\nrules:\n  - rule: greet\n    steps:\n      - intent: greet\n      - action: utter_greet\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(retraining_service.settings, "ROLE_PACKS_DIR", str(tmp_path))

    payload = yaml.safe_load(retraining_service._prepare_assets(
        "it", [{"name": "ask_vpn_renewal", "examples": ["renew my vpn certificate"]}]
    ))

    assert payload["pipeline"] == []
    assert "ask_vpn_renewal" in payload["intents"]
    assert {item["intent"] for item in payload["nlu"]} == {"greet", "ask_vpn_renewal"}
    assert payload["rules"][0]["rule"] == "greet"
    assert payload["responses"]["utter_greet"][0]["text"] == "Hi"
