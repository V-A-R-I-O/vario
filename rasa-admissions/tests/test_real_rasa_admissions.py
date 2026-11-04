"""Admissions on real Rasa 3.6, end to end (slice-39, A2-05).

Trains the full model (NLU + dialogue), then starts the real mock-admissions
service, the action server and `rasa run` with the shared VARIO channel, and
drives conversations through POST /webhooks/vario/converse exactly as the
gateway does. Needs `pip install -r requirements-rasa.txt` (Python 3.10).
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
MOCK = REPO / "mock-admissions-service"
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
    work = tmp_path_factory.mktemp("adm")
    env = {**os.environ, "RASA_TELEMETRY_ENABLED": "false", "RASA_CACHE_DIRECTORY": str(work / "cache"),
           "PYTHONPATH": os.pathsep.join([str(REPO / "rasa-shared"), str(PACK)])}
    subprocess.run([RASA, "train", "--out", str(work / "models"), "--fixed-model-name", "adm"],
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

    mock, mock_log = start("mock", [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(mock_port)], MOCK)
    _wait(f"http://127.0.0.1:{mock_port}/health", mock, mock_log)
    actions, actions_log = start("actions", [RASA, "run", "actions", "--actions", "actions", "--port", str(actions_port)],
                                 PACK, {"MOCK_ADMISSIONS_URL": f"http://127.0.0.1:{mock_port}"})
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
    def __init__(self, stack):
        self.url, self.sender = stack["url"], str(uuid.uuid4())

    def say(self, text):
        reply = httpx.post(self.url, json={"sender": self.sender, "message": text,
                                           "metadata": {"auth_context": {"employee_id": "APP-2026-001"}}},
                           timeout=60).json()
        card = reply.get("card")
        if card:
            missing = [f for f in REQUIRED[card["type"]] if not card.get(f)]
            assert not missing, f"{card['type']} card missing {missing}: {card}"
        return reply


def test_status_with_the_id_up_front(stack):
    r = Chat(stack).say("what is the status of application APP-1001?")
    assert r["intent"] == "check_application_status"
    assert r["card"]["type"] == "data_card"
    assert "Under Review" in r["response_text"]
    assert r["current_form"] is None


def test_unknown_application_is_a_graceful_not_found(stack):
    r = Chat(stack).say("status of APP-9999")
    assert r["card"]["type"] == "not_found"
    assert "APP-9999" in r["response_text"]


def test_prompt_then_id_and_the_next_request_asks_again(stack):
    chat = Chat(stack)
    r = chat.say("check my application status")
    assert (r["current_form"], r["current_step"]) == ("application_status_form", "application_id")
    r = chat.say("APP-1002")
    assert r["card"]["type"] == "data_card" and "APP-1002" in r["response_text"]
    r = chat.say("check my application status")  # M1b: no stale ID reuse
    assert r["current_form"] == "application_status_form"


def test_a_fee_question_interrupts_the_id_prompt(stack):
    chat = Chat(stack)
    chat.say("check my application status")
    r = chat.say("actually what is the MBA tuition fee?")  # M3c
    assert r["intent"] == "ask_fee_deadline"
    assert r["current_form"] is None
    assert "4,50,000" in r["response_text"]


def test_checklist_prompt_offers_programs_then_lists_documents(stack):
    chat = Chat(stack)
    r = chat.say("what documents do I need?")
    assert r["current_form"] == "checklist_form"
    assert r["card"]["type"] == "slot_prompt"
    assert [o["label"] for o in r["card"]["options"]] == ["B.Tech", "M.Tech", "MBA"]
    r = chat.say("MBA")
    assert r["card"]["type"] == "list" and r["card"]["items"]
    assert r["current_form"] is None


def test_checklist_with_the_program_up_front(stack):
    r = Chat(stack).say("what documents do I need for btech?")
    assert r["card"]["type"] == "list"


def test_fee_and_deadline_answers_come_from_the_calendar(stack):
    chat = Chat(stack)
    assert "4,50,000" in chat.say("what is the MBA tuition fee?")["response_text"]
    assert "November 30, 2026" in chat.say("when is the deadline?")["response_text"]


def test_greeting_and_goodbye(stack):
    chat = Chat(stack)
    assert "Admissions Assistant" in chat.say("hi")["response_text"]
    assert chat.say("bye")["response_text"]


def test_mock_outage_says_unavailable_not_found(stack):
    stack["mock"].terminate()
    stack["mock"].wait(timeout=30)
    r = Chat(stack).say("what is the status of application APP-1001?")  # M6b
    assert "unavailable" in r["response_text"].lower()
    assert "not found" not in r["response_text"].lower()


def test_pack_endpoints_load_through_rasa(monkeypatch):
    """The shipped endpoints.yml (used by docker compose) must expand every variable."""
    from rasa.core.utils import AvailableEndpoints

    env = {"ACTION_ENDPOINT_URL": "http://actions.test:5055/webhook", "POSTGRES_HOST": "postgres.test",
           "POSTGRES_DB": "rasa_admissions", "POSTGRES_USER": "vario", "POSTGRES_PASSWORD": "secret"}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    endpoints = AvailableEndpoints.read_endpoints(str(PACK / "endpoints.yml"))
    assert endpoints.action.url == env["ACTION_ENDPOINT_URL"]
    assert endpoints.tracker_store.type == "vario_rasa.tracker_store.RedactingSQLTrackerStore"
    assert endpoints.tracker_store.kwargs["db"] == "rasa_admissions"
