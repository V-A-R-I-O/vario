"""End-to-end tests of the shared channel and tracker store inside a real `rasa run`.

Needs `pip install -r rasa-shared/requirements.txt` (Rasa 3.6.20, Python 3.10).
The session fixture trains tests/fixture_bot once (~1 min) and starts Rasa on
a free port with the VARIO channel and the redacting SQLite tracker store.
"""
import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
import requests

from tests.conftest import CONTRACT_DIR, RASA_SHARED

BOT = Path(__file__).resolve().parent / "fixture_bot"
RASA = str(Path(sys.executable).parent / "rasa")
SECRET = "hunter2-very-secret-answer"


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def rasa_server(tmp_path_factory):
    work = tmp_path_factory.mktemp("rasa")
    db = work / "tracker.db"
    # Keep Rasa's training cache out of the repo.
    env = {**os.environ, "PYTHONPATH": str(RASA_SHARED), "VARIO_TEST_TRACKER_DB": str(db),
           "RASA_TELEMETRY_ENABLED": "false", "RASA_CACHE_DIRECTORY": str(work / "cache")}
    subprocess.run(
        [RASA, "train", "--config", "config.yml", "--domain", "domain.yml", "--data", "data",
         "--out", str(work / "models"), "--fixed-model-name", "fixture"],
        cwd=BOT, env=env, check=True, capture_output=True,
    )
    port = _free_port()
    log = open(work / "rasa.log", "w")
    proc = subprocess.Popen(
        [RASA, "run", "--enable-api", "--model", str(work / "models"), "--port", str(port),
         "--credentials", "credentials.yml", "--endpoints", "endpoints.yml"],
        cwd=BOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 180
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"rasa run exited; see {work / 'rasa.log'}")
        try:
            if requests.get(f"{base}/webhooks/vario/", timeout=2).status_code == 200:
                break
        except requests.ConnectionError:
            time.sleep(1)
    else:
        proc.terminate()
        raise RuntimeError(f"rasa run did not become ready; see {work / 'rasa.log'}")
    yield {"base": base, "db": db}
    proc.terminate()
    proc.wait(timeout=30)
    log.close()


def converse(server, sender, message, **metadata):
    res = requests.post(
        f"{server['base']}/webhooks/vario/converse",
        json={"sender": sender, "message": message, "metadata": metadata},
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def test_card_turn_returns_contract_fields(rasa_server):
    reply = converse(rasa_server, str(uuid.uuid4()), "what is my leave balance")
    fixture = json.loads((CONTRACT_DIR / "converse-response-card-turn.json").read_text())
    assert set(reply) == set(fixture)
    assert reply["intent"] == "check_balance"
    assert reply["confidence"] > 0.4
    assert reply["template_key"] == "check_leave_balance_response"
    assert reply["slots"] == {"total": 22}
    assert reply["card"]["type"] == "data_card"
    assert reply["response_text"] == "You have 22 days of leave remaining."
    assert reply["current_form"] is None and reply["sensitive_next_input"] is False


def test_plain_text_turn_has_no_card(rasa_server):
    reply = converse(rasa_server, str(uuid.uuid4()), "hello")
    assert reply["intent"] == "greet"
    assert reply["response_text"] == "Hello from the fixture bot."
    assert reply["card"] is None


def test_metadata_reaches_the_tracker(rasa_server):
    sender = str(uuid.uuid4())
    converse(rasa_server, sender, "hello", auth_context={"employee_id": "EMP-1001"})
    tracker = requests.get(f"{rasa_server['base']}/conversations/{sender}/tracker", timeout=10).json()
    assert tracker["latest_message"]["metadata"]["auth_context"]["employee_id"] == "EMP-1001"


def test_trackers_are_isolated_per_sender(rasa_server):
    first, second = str(uuid.uuid4()), str(uuid.uuid4())
    assert converse(rasa_server, first, "I want to apply for leave")["current_form"] == "leave_form"
    assert converse(rasa_server, second, "hello")["current_form"] is None


def test_form_turn_reports_form_step_and_sensitive_flag(rasa_server):
    reply = converse(rasa_server, str(uuid.uuid4()), "I want to apply for leave")
    assert reply["current_form"] == "leave_form"
    assert reply["current_step"] == "leave_reason"
    assert reply["sensitive_next_input"] is True
    assert reply["response_text"] == "Tell me the secret reason."


def test_sensitive_answer_is_used_but_never_stored(rasa_server):
    sender = str(uuid.uuid4())
    converse(rasa_server, sender, "I want to apply for leave")
    done = converse(rasa_server, sender, SECRET, sensitive=True)
    assert done["current_form"] is None
    assert done["response_text"] == "Leave recorded."

    with sqlite3.connect(rasa_server["db"]) as conn:
        rows = [r[0] for r in conn.execute("SELECT data FROM events WHERE sender_id = ?", (sender,))]
    assert rows, "tracker events were not persisted"
    assert not any(SECRET in data for data in rows)
    assert any("[redacted]" in data for data in rows)


def test_malformed_request_is_rejected(rasa_server):
    res = requests.post(f"{rasa_server['base']}/webhooks/vario/converse", json={"message": "hi"}, timeout=10)
    assert res.status_code == 400
