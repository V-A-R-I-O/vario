"""HR on real Rasa 3.6, end to end (slice-35, audit 2).

Trains the full model, starts the real mock-hrms, the action server and
`rasa run` with the shared VARIO channel, and drives the HR flows through
POST /webhooks/vario/converse exactly as the gateway does. Needs
`pip install -r requirements-rasa.txt` (Python 3.10).
"""
import os
import socket
import subprocess
import sys
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

import httpx
import pytest

PACK = Path(__file__).resolve().parents[1]
REPO = PACK.parent
MOCK = REPO / "mock-hrms-service"
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
    work = tmp_path_factory.mktemp("hr")
    env = {**os.environ, "RASA_TELEMETRY_ENABLED": "false", "RASA_CACHE_DIRECTORY": str(work / "cache"),
           "PYTHONPATH": os.pathsep.join([str(REPO / "rasa-shared"), str(PACK)])}
    subprocess.run([RASA, "train", "--out", str(work / "models"), "--fixed-model-name", "hr"],
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
                                 PACK, {"MOCK_HRMS_URL": f"http://127.0.0.1:{mock_port}"})
    _wait(f"http://127.0.0.1:{actions_port}/health", actions, actions_log)
    rasa, rasa_log = start("rasa", [RASA, "run", "--enable-api", "--port", str(rasa_port), "--model", str(work / "models"),
                                    "--credentials", "credentials.yml", "--endpoints", str(endpoints)], PACK)
    _wait(f"http://127.0.0.1:{rasa_port}/webhooks/vario/", rasa, rasa_log)

    yield {"url": f"http://127.0.0.1:{rasa_port}/webhooks/vario/converse",
           "mock_url": f"http://127.0.0.1:{mock_port}", "mock": mock}
    for proc in procs:
        proc.terminate()
    for proc in procs:
        proc.wait(timeout=30)


class Chat:
    def __init__(self, stack, employee_id="EMP-1001", name="Employee One"):
        self.url, self.sender = stack["url"], str(uuid.uuid4())
        self.auth = {"employee_id": employee_id, "full_name": name, "role": "end_user"}

    def say(self, text):
        reply = httpx.post(self.url, json={"sender": self.sender, "message": text,
                                           "metadata": {"auth_context": self.auth}}, timeout=60).json()
        card = reply.get("card")
        if card:
            missing = [f for f in REQUIRED[card["type"]] if not card.get(f)]
            assert not missing, f"{card['type']} card missing {missing}: {card}"
        return reply


def _days_ahead(n):
    return (date.today() + timedelta(days=n)).isoformat()


def test_balance_uses_the_signed_in_employee(stack):
    r = Chat(stack).say("what is my leave balance?")  # B6
    assert r["intent"] == "check_leave_balance"
    assert r["card"]["type"] == "data_card"
    assert r["current_form"] is None


def test_an_employee_id_typed_in_chat_is_ignored(stack):
    r = Chat(stack).say("what is the leave balance for EMP-1042")  # M2a
    assert "Employee One" in r["card"]["title"]


def test_leave_request_keeps_the_dates_as_entered(stack):
    start, end = _days_ahead(20), _days_ahead(22)
    chat = Chat(stack, "EMP-1013", "Mitesh")
    r = chat.say("I want to apply for leave")
    assert r["card"]["type"] == "slot_prompt" and r["card"]["options"]
    chat.say("annual")
    assert chat.say(start)["current_step"] == "end_date"
    assert chat.say(end)["current_step"] == "reason"
    r = chat.say("family function")
    assert r["card"]["type"] == "confirmation"  # A2-07: rows, not options
    rows = {row["label"]: row["value"] for row in r["card"]["rows"]}
    assert (rows["Start date"], rows["End date"]) == (start, end)  # A2-06
    r = chat.say("confirm")
    assert r["card"]["type"] == "result" and r["card"]["referenceId"]
    stored = httpx.get(f"{stack['mock_url']}/employees/EMP-1013/leave-status", timeout=10).json()["applications"]
    latest = next(a for a in stored if a["reference_id"] == r["card"]["referenceId"])
    assert (latest["start_date"], latest["end_date"]) == (start, end)
    assert chat.say("I want to apply for leave")["current_step"] == "leave_type"  # M1a


def test_cancel_leaves_the_form_at_any_step(stack):
    chat = Chat(stack)
    chat.say("I want to apply for leave")
    chat.say("sick")
    r = chat.say("cancel")  # M3a
    assert r["current_form"] is None


def test_a_balance_question_mid_form_is_answered_and_the_form_resumes(stack):
    chat = Chat(stack)
    chat.say("I want to apply for leave")
    chat.say("casual")
    r = chat.say("what is my leave balance?")  # M3a
    assert r["card"]["type"] == "data_card"
    assert (r["current_form"], r["current_step"]) == ("leave_request_form", "start_date")


def test_natural_language_dates_are_accepted(stack):
    chat = Chat(stack)
    chat.say("I want to apply for leave")
    chat.say("sick")
    assert chat.say("next monday")["current_step"] == "end_date"  # N5


def test_an_unsupported_policy_gets_an_honest_answer(stack):
    r = Chat(stack).say("what is the travel reimbursement policy?")  # M4a
    assert r["intent"] == "ask_unsupported_policy"
    assert "HR portal" in r["response_text"]


@pytest.mark.parametrize("question, template_key, expected", [
    ("what is the maternity policy?", "ask_maternity_policy_response", "26 weeks"),
    ("how many days of paternity leave do I get?", "ask_paternity_policy_response", "2 weeks"),
    ("tell me about the bereavement leave guidelines", "ask_bereavement_policy_response", "5 consecutive"),
    ("can I carry forward unused leaves to next year?", "ask_carry_forward_policy_response", "carry forward up to 5"),
    ("do I need a medical certificate for sick leave?", "ask_sick_policy_response", "medical certificate"),
])
def test_each_policy_topic_gets_its_own_answer(stack, question, template_key, expected):
    r = Chat(stack).say(question)  # M4b
    assert r["template_key"] == template_key
    assert expected in r["response_text"]


def test_the_general_leave_policy_question_still_gets_the_overview(stack):
    r = Chat(stack).say("what is the company leave policy?")
    assert r["template_key"] == "ask_policy_faq_response"


def test_a_topic_question_mid_form_is_answered_and_the_form_resumes(stack):
    chat = Chat(stack)
    chat.say("I want to apply for leave")
    r = chat.say("what is the maternity policy?")
    assert r["template_key"] == "ask_maternity_policy_response"
    assert (r["current_form"], r["current_step"]) == ("leave_request_form", "leave_type")


def test_greeting_and_goodbye(stack):
    chat = Chat(stack)
    assert "HR Assistant" in chat.say("hi")["response_text"]  # M5a
    assert chat.say("bye")["response_text"]


def test_hrms_outage_says_unavailable(stack):
    stack["mock"].terminate()
    stack["mock"].wait(timeout=30)
    r = Chat(stack).say("what is my leave balance?")  # B2a
    assert "unavailable" in r["response_text"].lower()
