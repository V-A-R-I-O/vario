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
        lambda pack, rows: ("config: test", "intents: []", b"training archive"),
    )

    train_response = MagicMock()
    train_response.raise_for_status = MagicMock()
    reload_response = MagicMock()
    reload_response.raise_for_status = MagicMock()

    client = MagicMock()
    client.post = AsyncMock(side_effect=[train_response, reload_response])
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=client)
    context.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.retraining_service.httpx.AsyncClient", return_value=context):
        await retraining_service.train(
            "it", [{"name": "ask_vpn_renewal", "examples": ["renew my vpn certificate"]}]
        )

    assert client.post.await_count == 2
    first_call, second_call = client.post.await_args_list
    assert first_call.args[0] == "http://rasa-it:5006/model/train"
    assert first_call.kwargs["data"]["save_to_default_model_directory"] == "true"
    assert first_call.kwargs["files"]["training_files"][0] == "training-data.zip"
    assert first_call.kwargs["files"]["training_files"][1] == b"training archive"
    assert second_call.args[0] == "http://rasa-it:5006/model/reload"
    assert not first_call.kwargs.get("headers")
