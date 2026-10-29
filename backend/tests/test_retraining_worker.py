"""Worker-level tests for Slice 10 retraining outcomes and model activation."""
import io
import zipfile

import pytest
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


@pytest.mark.asyncio
@pytest.mark.parametrize("pack", ["hr", "it", "admissions"])
async def test_rasa_training_activates_model_after_training(monkeypatch, pack):
    calls = []

    class Response:
        headers = {"filename": "it-model.tar.gz"}

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs))
            return Response()

        async def put(self, url, **kwargs):
            calls.append(("PUT", url, kwargs))
            return Response()

    monkeypatch.setattr(service.httpx, "AsyncClient", Client)
    monkeypatch.setattr(
        service,
        "_prepare_assets",
        lambda _pack, _rows: "version: \"3.1\"\nintents: []\n",
    )

    await service.train(pack, [{"name": "new_intent", "examples": ["example"]}])

    assert len(calls) == 2
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/model/train?save_to_default_model_directory=true")
    assert calls[1][0] == "PUT"
    assert calls[1][1].endswith("/model")
    assert calls[0][2]["headers"]["Content-Type"] == "application/x-yaml"
    assert "intents:" in calls[0][2]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("pack", ["hr", "it", "admissions"])
async def test_rasa_training_fails_if_model_reload_fails(monkeypatch, pack):
    calls = []

    class Response:
        headers = {"filename": "it-model.tar.gz"}

        def __init__(self, status=200):
            self.status = status

        def raise_for_status(self):
            if self.status >= 400:
                raise RuntimeError(f"HTTP {self.status}")

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs))
            return Response(200)

        async def put(self, url, **kwargs):
            calls.append(("PUT", url, kwargs))
            return Response(500 if url.endswith("/model") else 200)

    monkeypatch.setattr(service.httpx, "AsyncClient", Client)
    monkeypatch.setattr(
        service,
        "_prepare_assets",
        lambda _pack, _rows: "version: \"3.1\"\nintents: []\n",
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        await service.train(pack, [{"name": "new_intent", "examples": ["example"]}])

    assert len(calls) == 2
    assert calls[0][1].endswith("/model/train?save_to_default_model_directory=true")
    assert calls[1][1].endswith("/model")


@pytest.mark.asyncio
async def test_it_training_uses_real_rasa_model_api(monkeypatch):
    calls = []

    class Response:
        headers = {"filename": "it-model.tar.gz"}

        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, **kwargs):
            calls.append(("POST", url, kwargs))
            return Response()

        async def put(self, url, **kwargs):
            calls.append(("PUT", url, kwargs))
            return Response()

    monkeypatch.setattr(service.httpx, "AsyncClient", Client)
    monkeypatch.setattr(
        service,
        "_prepare_assets",
        lambda _pack, _rows: "version: \"3.1\"\nintents: []\n",
    )
    await service.train(
        "it", [{"name": "ask_vpn_renewal", "examples": ["renew my vpn certificate"]}]
    )

    assert len(calls) == 2
    assert calls[0][0] == "POST"
    assert calls[0][1].endswith("/model/train")
    assert calls[0][2]["headers"]["Content-Type"] == "application/x-yaml"
    assert "intents:" in calls[0][2]["content"]
    assert calls[1][0] == "PUT"
    assert calls[1][1].endswith("/model")
    assert calls[1][2]["json"] == {"model_file": "models/it-model.tar.gz"}
