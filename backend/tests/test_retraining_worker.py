"""Worker-level tests for Slice 10 retraining outcomes and model activation."""
import json
from pathlib import Path

import httpx
import pytest
import yaml
from sqlalchemy import select

from app.models.intent import Intent
from app.models.retraining_job import RetrainingJob
from app.services import retraining_service as service


@pytest.mark.asyncio
async def test_worker_success_activates_model_and_clears_dirty_flag(
    monkeypatch, db_session
):
    intent = Intent(
        intent_id="slice10-hr-dirty",
        role_pack="hr",
        name="slice10_hr_test_intent",
        intent_type="static_faq",
        needs_retrain=True,
    )
    job = RetrainingJob(
        job_id="slice10-success-job",
        role_pack="hr",
        actor_id="slice10-admin",
        state="pending",
    )
    db_session.add_all([intent, job])
    await db_session.commit()

    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr(service, "AsyncSessionLocal", TestingSessionLocal)

    async def load_rows(_pack):
        return ([{"name": intent.name, "examples": ["new HR example"]}], [intent.intent_id])

    activated = []

    async def train(pack, rows):
        activated.append((pack, rows))

    monkeypatch.setattr(service, "load_rows", load_rows)
    monkeypatch.setattr(service, "train", train)

    await service.run(job.job_id, "hr")

    await db_session.refresh(intent)
    await db_session.refresh(job)
    assert activated == [("hr", [{"name": intent.name, "examples": ["new HR example"]}])]
    assert intent.needs_retrain is False
    assert job.state == "complete"
    assert job.intent_count == 1
    assert job.completed_at is not None
    assert job.error_message is None


@pytest.mark.asyncio
async def test_worker_failure_keeps_dirty_flag_and_marks_job_failed(
    monkeypatch, db_session
):
    intent = Intent(
        intent_id="slice10-admissions-dirty",
        role_pack="admissions",
        name="slice10_admissions_test_intent",
        intent_type="static_faq",
        needs_retrain=True,
    )
    job = RetrainingJob(
        job_id="slice10-failure-job",
        role_pack="admissions",
        actor_id="slice10-admin",
        state="pending",
    )
    db_session.add_all([intent, job])
    await db_session.commit()

    from tests.conftest import TestingSessionLocal
    monkeypatch.setattr(service, "AsyncSessionLocal", TestingSessionLocal)

    async def load_rows(_pack):
        return ([{"name": intent.name, "examples": ["new admissions example"]}], [intent.intent_id])

    async def fail_activation(_pack, _rows):
        raise RuntimeError("model reload failed")

    monkeypatch.setattr(service, "load_rows", load_rows)
    monkeypatch.setattr(service, "train", fail_activation)

    await service.run(job.job_id, "admissions")

    await db_session.refresh(intent)
    await db_session.refresh(job)
    assert intent.needs_retrain is True
    assert job.state == "failed"
    assert job.completed_at is not None
    assert "RuntimeError" in job.error_message


REPO = Path(__file__).resolve().parents[2]
FAQ = {"name": "ask_parking_policy", "examples": ["where can I park"], "answer": "Use the P2 lot."}


def _pack(tmp_path, monkeypatch):
    root = tmp_path / "hr"
    (root / "data").mkdir(parents=True)
    (root / "config.yml").write_text("recipe: default.v1\nlanguage: en\npipeline: []\npolicies: []\n")
    (root / "domain.yml").write_text(
        "version: '3.1'\nintents:\n  - submit_leave_request\nresponses:\n  utter_greet:\n    - text: Hi\n"
    )
    (root / "data" / "nlu.yml").write_text(
        "version: '3.1'\nnlu:\n- intent: submit_leave_request\n  examples: |\n"
        "    - apply for [sick](leave_type) leave\n    - I want leave\n"
        "- regex: application_id\n  examples: |\n    - \\bAPP-\\d{4}\\b\n"
    )
    (root / "data" / "rules.yml").write_text("version: '3.1'\nrules: []\n")
    monkeypatch.setattr(service.settings, "ROLE_PACKS_DIR", str(tmp_path))
    return root


def _nlu(document, intent):
    return next(item for item in document["nlu"] if item.get("intent") == intent)


def test_training_yaml_keeps_annotated_examples_and_adds_new_phrases(tmp_path, monkeypatch):
    _pack(tmp_path, monkeypatch)
    rows = [{"name": "submit_leave_request", "examples": ["apply for sick leave", "book time off"], "answer": None}]

    document = yaml.safe_load(service.build_training_yaml("hr", rows))

    examples = _nlu(document, "submit_leave_request")["examples"].splitlines()
    # The annotated form example survives; its plain duplicate from the DB is not re-added.
    assert examples == ["- apply for [sick](leave_type) leave", "- I want leave", "- book time off"]
    assert any(item.get("regex") == "application_id" for item in document["nlu"])
    assert document["recipe"] == "default.v1" and document["version"] == "3.1"


def test_training_yaml_teaches_rasa_a_new_static_faq(tmp_path, monkeypatch):
    _pack(tmp_path, monkeypatch)

    document = yaml.safe_load(service.build_training_yaml("hr", [FAQ]))

    assert "ask_parking_policy" in document["intents"]
    assert _nlu(document, "ask_parking_policy")["examples"] == "- where can I park\n"
    assert document["responses"]["utter_ask_parking_policy"] == [
        {"text": "Use the P2 lot.", "custom": {"vario": {"template_key": "ask_parking_policy_response"}}}
    ]
    assert {"rule": "Answer ask_parking_policy",
            "steps": [{"intent": "ask_parking_policy"}, {"action": "utter_ask_parking_policy"}]} in document["rules"]
    assert document["responses"]["utter_greet"] == [{"text": "Hi"}]


def test_training_yaml_skips_unknown_intents_without_an_answer(tmp_path, monkeypatch):
    _pack(tmp_path, monkeypatch)

    document = yaml.safe_load(
        service.build_training_yaml("hr", [{"name": "ghost_intent", "examples": ["boo"], "answer": None}])
    )

    assert "ghost_intent" not in document["intents"]
    assert all(item.get("intent") != "ghost_intent" for item in document["nlu"])


@pytest.mark.parametrize("pack", ["hr", "it", "admissions"])
def test_training_yaml_builds_from_the_repo_packs(monkeypatch, pack):
    # A native run points ROLE_PACKS_DIR at the repo, whose folders are rasa-<pack>.
    monkeypatch.setattr(service.settings, "ROLE_PACKS_DIR", str(REPO))

    document = yaml.safe_load(service.build_training_yaml(pack, [FAQ]))

    assert document["pipeline"] and document["policies"] and document["forms"]
    assert "utter_ask_parking_policy" in document["responses"]


def _client(monkeypatch, handler):
    calls = []
    real = httpx.AsyncClient

    def record(request):
        calls.append(request)
        return handler(request)

    monkeypatch.setattr(
        service.httpx, "AsyncClient", lambda **kwargs: real(transport=httpx.MockTransport(record), **kwargs)
    )
    return calls


@pytest.mark.asyncio
@pytest.mark.parametrize("pack", ["hr", "it", "admissions"])
async def test_rasa_training_loads_the_trained_model(tmp_path, monkeypatch, pack):
    monkeypatch.setattr(service.settings, "ROLE_PACKS_DIR", str(REPO))
    monkeypatch.setattr(service.settings, "RETRAINING_INTERNAL_TOKEN", "test-only-token")
    calls = _client(
        monkeypatch,
        lambda request: httpx.Response(200, headers={"filename": "20261104-new.tar.gz"}, content=b"model"),
    )

    await service.train(pack, [FAQ])

    train_call, load_call = calls
    assert (train_call.method, train_call.url.path) == ("POST", "/model/train")
    assert train_call.headers["content-type"] == "application/x-yaml"
    assert train_call.url.params["save_to_default_model_directory"] == "true"
    assert train_call.url.params["token"] == "test-only-token"
    assert "ask_parking_policy" in yaml.safe_load(train_call.content)["intents"]
    assert (load_call.method, load_call.url.path) == ("PUT", "/model")
    assert load_call.url.params["token"] == "test-only-token"
    assert json.loads(load_call.read()) == {"model_file": "models/20261104-new.tar.gz"}


@pytest.mark.asyncio
async def test_rasa_training_fails_if_model_load_fails(monkeypatch):
    monkeypatch.setattr(service.settings, "ROLE_PACKS_DIR", str(REPO))
    calls = _client(
        monkeypatch,
        lambda request: httpx.Response(500) if request.method == "PUT"
        else httpx.Response(200, headers={"filename": "m.tar.gz"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await service.train("hr", [FAQ])

    assert [call.method for call in calls] == ["POST", "PUT"]
    assert "token" not in calls[0].url.params


@pytest.mark.asyncio
async def test_rasa_training_fails_without_a_model_filename(monkeypatch):
    monkeypatch.setattr(service.settings, "ROLE_PACKS_DIR", str(REPO))
    calls = _client(monkeypatch, lambda request: httpx.Response(200))

    with pytest.raises(RuntimeError, match="filename"):
        await service.train("hr", [FAQ])

    assert [call.method for call in calls] == ["POST"]
