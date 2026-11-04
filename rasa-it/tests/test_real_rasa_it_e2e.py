"""IT on real Rasa 3.6, end to end (slice-37, audit 2).

Trains the full model, starts the real mock-itsm, the action server and
`rasa run` with the shared VARIO channel, and drives the IT flows through
POST /webhooks/vario/converse exactly as the gateway does.
"""
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
import pytest

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parent
MOCK = REPO / "mock-itsm-service"
RASA = str(Path(sys.executable).parent / "rasa")

# Fields each card type needs for the UI to render it (frontend/src/components/chat/types.ts).
REQUIRED = {
    "plain_text": ["text"], "faq_answer": ["text"], "error": ["text"], "not_found": ["text"],
    "result": ["text"], "data_card": ["rows"], "confirmation": ["rows"],
    "slot_prompt": ["text", "options"], "list": ["items"],
}


def _port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait(url, proc, log, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"process exited; see {log}")
        try:
            httpx.get(url, timeout=2)
            return
        except httpx.HTTPError:
            time.sleep(1)
    raise RuntimeError(f"{url} not ready; see {log}")


@pytest.fixture(scope="session")
def stack(tmp_path_factory):
    work = tmp_path_factory.mktemp("it")
    env = {**os.environ, "RASA_TELEMETRY_ENABLED": "false", "RASA_CACHE_DIRECTORY": str(work / "cache"),
           "PYTHONPATH": os.pathsep.join([str(REPO / "rasa-shared"), str(PACK)])}
    subprocess.run([RASA, "train", "--out", str(work / "models"), "--fixed-model-name", "it"],
                   cwd=PACK, env=env, check=True, capture_output=True)

    mock_port, actions_port, rasa_port = _port(), _port(), _port()
    endpoints = work / "endpoints.yml"
    endpoints.write_text(
        f"action_endpoint:\n  url: http://127.0.0.1:{actions_port}/webhook\n"
        "tracker_store:\n  type: vario_rasa.tracker_store.RedactingSQLTrackerStore\n"
        f"  dialect: sqlite\n  db: {work / 'tracker.db'}\n",
        encoding="utf-8",
    )
    procs = []

    def start(name, cmd, cwd, extra_env=None):
        log = open(work / f"{name}.log", "w")
        proc = subprocess.Popen(cmd, cwd=cwd, env={**env, **(extra_env or {})}, stdout=log, stderr=subprocess.STDOUT)
        procs.append(proc)
        return proc, work / f"{name}.log"

    mock, mock_log = start("mock", [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(mock_port)], MOCK,
                           {"IDENTITY_ATTEMPTS_PATH": str(work / "attempts.json")})
    _wait(f"http://127.0.0.1:{mock_port}/health", mock, mock_log)
    actions, actions_log = start("actions", [RASA, "run", "actions", "--actions", "actions", "--port", str(actions_port)],
                                 PACK, {"MOCK_ITSM_URL": f"http://127.0.0.1:{mock_port}"})
    _wait(f"http://127.0.0.1:{actions_port}/health", actions, actions_log)
    rasa, rasa_log = start("rasa", [RASA, "run", "--enable-api", "--port", str(rasa_port), "--model", str(work / "models"),
                                    "--credentials", "credentials.yml", "--endpoints", str(endpoints)], PACK)
    _wait(f"http://127.0.0.1:{rasa_port}/webhooks/vario/", rasa, rasa_log)

    yield {"url": f"http://127.0.0.1:{rasa_port}/webhooks/vario/converse", "mock": mock}
    for proc in procs:
        proc.terminate()
    for proc in procs:
        proc.wait(timeout=30)


class Chat:
    def __init__(self, stack, employee_id="EMP-1001"):
        self.url, self.sender = stack["url"], str(uuid.uuid4())
        self.auth = {"employee_id": employee_id, "full_name": employee_id, "role": "end_user"}

    def say(self, text):
        reply = httpx.post(self.url, json={"sender": self.sender, "message": text,
                                           "metadata": {"auth_context": self.auth}}, timeout=60).json()
        card = reply.get("card")
        if card:
            missing = [f for f in REQUIRED[card["type"]] if not card.get(f)]
            assert not missing, f"{card['type']} card missing {missing}: {card}"
        return reply


def test_status_lookup_and_cancel(stack):
    chat = Chat(stack)
    assert chat.say("check my ticket status")["current_form"] == "ticket_status_form"
    assert chat.say("cancel")["current_form"] is None  # M3b
    r = Chat(stack).say("what is the status of ticket IT-1002?")
    assert r["card"]["type"] == "data_card"


@pytest.mark.parametrize("opening, steps", [
    ("my laptop screen is broken, I want to raise a ticket", []),
    ("my laptop screen is broken, I want to raise a ticket", ["hardware"]),
    ("I forgot my password", []),
])
def test_cancel_ends_ticket_creation_and_password_reset(stack, opening, steps):
    chat = Chat(stack, "EMP-1012")
    chat.say(opening)
    for step in steps:
        chat.say(step)
    r = chat.say("cancel")
    assert r["intent"] == "cancel"
    assert r["current_form"] is None and r["current_step"] is None
    assert r["card"] is None or r["card"]["type"] != "confirmation"


def test_unknown_ticket_is_a_not_found_card(stack):
    r = Chat(stack).say("status of ticket IT-9999")
    assert r["card"]["type"] == "not_found"


def test_ticket_creation_confirms_details_and_audits(stack):
    chat = Chat(stack, "EMP-1012")
    r = chat.say("my laptop screen is broken, I want to raise a ticket")
    assert r["card"]["type"] == "slot_prompt" and "Hardware" in [o["label"] for o in r["card"]["options"]]
    chat.say("hardware")
    r = chat.say("the laptop screen flickers and goes black")
    assert r["card"]["type"] == "confirmation"  # A2-12
    rows = {row["label"]: row["value"] for row in r["card"]["rows"]}
    assert rows == {"Category": "hardware", "Description": "the laptop screen flickers and goes black",
                    "Reporter": "EMP-1012"}
    r = chat.say("confirm")
    ticket_id = r["card"]["referenceId"]  # A2-11
    assert r["card"]["type"] == "result" and ticket_id.startswith("IT-")
    assert ticket_id in r["response_text"]
    assert r["audit_event"] == {"action_type": "ticket_created", "reference_id": ticket_id,
                                "details": {"category": "hardware", "reporter": "EMP-1012"}}  # A2-10


def test_password_reset_uses_the_signed_in_account_without_looping(stack):
    chat = Chat(stack, "EMP-1012")
    chat.say("I forgot my password")
    r = chat.say("EMP-1001")  # A2-13: someone else's ID
    assert "signed-in account, EMP-1012" in r["response_text"]
    assert r["current_step"] == "security_answer"
    r = chat.say("north campus")
    assert r["card"]["type"] == "result" and r["card"]["referenceId"] == "EMP-1012"
    assert r["audit_event"]["action_type"] == "password_reset_initiated"
    assert r["audit_event"]["reference_id"] == "EMP-1012"


def test_itsm_outage_is_an_error_card(stack):
    stack["mock"].terminate()
    stack["mock"].wait(timeout=30)
    r = Chat(stack).say("what is the status of ticket IT-1002?")
    assert r["card"]["type"] == "error"
