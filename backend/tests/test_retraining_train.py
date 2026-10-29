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
