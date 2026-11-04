"""Role-pack scoped retraining jobs (Slice 10)."""
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.intent import Intent
from app.models.response_template import ResponseTemplate
from app.models.retraining_job import RetrainingJob
from app.models.training_phrase import TrainingPhrase

log = logging.getLogger(__name__)
URLS = {
    "hr": settings.RASA_HR_URL,
    "it": settings.RASA_IT_URL,
    "admissions": settings.RASA_ADMISSIONS_URL,
}
ACTIVE_STATES = ("pending", "training")


def now():
    return datetime.now(timezone.utc)


async def load_rows(pack):
    """Every intent of the pack with its phrases; static FAQs also carry their answer text."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Intent).where(Intent.role_pack == pack).order_by(Intent.name)
        )
        intents = list(result.scalars().all())
        rows = []
        dirty = []
        for intent in intents:
            result = await db.execute(
                select(TrainingPhrase.phrase_text)
                .where(TrainingPhrase.intent_id == intent.intent_id)
                .order_by(TrainingPhrase.created_at)
            )
            phrases = [row[0].strip() for row in result.all() if row[0] and row[0].strip()]
            answer = None
            if intent.intent_type == "static_faq":
                answer = (await db.execute(
                    select(ResponseTemplate.base_text).where(
                        ResponseTemplate.template_key == f"{intent.name}_response",
                        ResponseTemplate.role_pack == pack,
                    )
                )).scalar_one_or_none()
            rows.append({"name": intent.name, "examples": phrases, "answer": answer})
            if intent.needs_retrain:
                dirty.append(intent.intent_id)
        return rows, dirty


_ANNOTATION = re.compile(r"\[([^\]]+)\]\([^)]+\)|\[([^\]]+)\]\{[^}]*\}")


def _plain(example: str) -> str:
    """`check my [casual](leave_type) balance` -> `check my casual balance` (for de-duplication)."""
    text = _ANNOTATION.sub(lambda m: m.group(1) or m.group(2), example)
    return " ".join(text.split()).casefold()


def _read_yaml(path: Path, default: Any) -> Any:
    return (yaml.safe_load(path.read_text(encoding="utf-8")) or default) if path.is_file() else default


def build_training_yaml(pack, rows) -> str:
    """One Rasa training document: the pack's own config, domain, NLU, rules and stories,
    plus the admin console's intents and phrases.

    Existing examples are kept (they carry entity annotations the forms rely on); new
    phrases are appended. A static FAQ the pack doesn't know yet gets an intent, an
    `utter_<name>` response whose template_key lets the gateway render the editable
    template, and a rule.
    """
    base = Path(settings.ROLE_PACKS_DIR)
    # Compose mounts packs as /rolepacks/<pack>; a native run points at the repo (rasa-<pack>).
    root = base / pack if (base / pack).is_dir() else base / f"rasa-{pack}"
    config = _read_yaml(root / "config.yml", None)
    domain = _read_yaml(root / "domain.yml", None)
    if not config or not domain:
        raise RuntimeError(f"Training assets unavailable for {pack}; check role-pack mounts.")
    nlu = _read_yaml(root / "data" / "nlu.yml", {}).get("nlu", [])
    rules = _read_yaml(root / "data" / "rules.yml", {}).get("rules", [])
    stories = _read_yaml(root / "data" / "stories.yml", {}).get("stories", [])

    intents = domain.setdefault("intents", [])
    known = {item if isinstance(item, str) else next(iter(item)) for item in intents}
    responses = domain.setdefault("responses", {})
    by_intent = {item["intent"]: item for item in nlu if "intent" in item}

    for row in rows:
        name, phrases = row["name"], row["examples"]
        if not phrases:
            continue
        if name not in known and not row.get("answer"):
            log.warning("Skipping intent %s: not in the %s domain and has no answer", name, pack)
            continue
        item = by_intent.get(name)
        if item is None:
            item = {"intent": name, "examples": ""}
            nlu.append(item)
            by_intent[name] = item
        lines = [line for line in str(item.get("examples", "")).splitlines() if line.strip()]
        seen = {_plain(line.lstrip("- ").strip()) for line in lines}
        lines += [f"- {p}" for p in phrases if _plain(p) not in seen]
        item["examples"] = "\n".join(lines) + "\n"

        if name not in known and row.get("answer"):
            intents.append(name)
            known.add(name)
            responses[f"utter_{name}"] = [{
                "text": row["answer"],
                "custom": {"vario": {"template_key": f"{name}_response"}},
            }]
            rules.append({"rule": f"Answer {name}", "steps": [{"intent": name}, {"action": f"utter_{name}"}]})

    document = {**config, **domain, "version": "3.1", "nlu": nlu, "rules": rules, "stories": stories}
    return yaml.safe_dump(document, sort_keys=False, allow_unicode=True)


async def train(pack, rows):
    """Train through Rasa's own API and load the result: POST /model/train, then PUT /model."""
    base = URLS[pack].rstrip("/")
    params = {"token": settings.RETRAINING_INTERNAL_TOKEN} if settings.RETRAINING_INTERNAL_TOKEN else {}
    async with httpx.AsyncClient(timeout=httpx.Timeout(900, connect=5)) as client:
        # Rasa replies with the model archive itself; only the filename header is needed.
        async with client.stream(
            "POST",
            f"{base}/model/train",
            params={**params, "save_to_default_model_directory": "true"},
            content=build_training_yaml(pack, rows).encode("utf-8"),
            headers={"Content-Type": "application/x-yaml"},
        ) as response:
            response.raise_for_status()
            filename = response.headers.get("filename")
        if not filename:
            raise RuntimeError("Rasa trained a model but did not report its filename")
        # Saved under the server's default model directory, relative to its working dir.
        response = await client.put(f"{base}/model", params=params, json={"model_file": f"models/{filename}"})
        response.raise_for_status()


async def _update_job(job_id, **values):
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(RetrainingJob).where(RetrainingJob.job_id == job_id).values(**values)
        )
        await db.commit()


async def run(job_id, pack):
    await _update_job(job_id, state="training", started_at=now())
    try:
        rows, dirty = await load_rows(pack)
        if not rows:
            raise RuntimeError("No intents are configured for this role pack")
        await train(pack, rows)
        if dirty:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(Intent)
                    .where(Intent.role_pack == pack, Intent.intent_id.in_(dirty))
                    .values(needs_retrain=False)
                )
                await db.commit()
        await _update_job(
            job_id, state="complete", completed_at=now(), intent_count=len(rows), error_message=None
        )
    except Exception as exc:
        log.exception("Retraining job failed: %s", job_id)
        await _update_job(
            job_id,
            state="failed",
            completed_at=now(),
            error_message=f"Retraining failed ({type(exc).__name__}); check service logs.",
        )


async def recover_stale_jobs():
    """Fail jobs interrupted by a process restart instead of leaving them pending forever."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(RetrainingJob)
            .where(RetrainingJob.state.in_(ACTIVE_STATES))
            .values(
                state="failed",
                completed_at=now(),
                error_message="Retraining was interrupted by a backend restart; start a new job.",
            )
        )
        await db.commit()


async def create_job(pack, actor):
    job_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as db:
        active = await db.execute(
            select(RetrainingJob.job_id).where(
                RetrainingJob.role_pack == pack,
                RetrainingJob.state.in_(ACTIVE_STATES),
            ).limit(1)
        )
        if active.scalar_one_or_none():
            raise ValueError("A retraining job is already running for this role pack.")
        db.add(RetrainingJob(
            job_id=job_id,
            role_pack=pack,
            actor_id=actor,
            state="pending",
            created_at=now(),
        ))
        try:
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ValueError("A retraining job is already running for this role pack.") from exc
    import asyncio
    asyncio.create_task(run(job_id, pack))
    return {"retrain_job_id": job_id}


async def get_job(job_id, pack):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(RetrainingJob).where(
                RetrainingJob.job_id == job_id,
                RetrainingJob.role_pack == pack,
            )
        )
        job = result.scalars().first()
        if job is None:
            return None
        return {
            "job_id": job.job_id,
            "role_pack": job.role_pack,
            "state": job.state,
            "created_at": job.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "started_at": job.started_at.replace(tzinfo=timezone.utc).isoformat() if job.started_at else None,
            "completed_at": job.completed_at.replace(tzinfo=timezone.utc).isoformat() if job.completed_at else None,
            "intent_count": job.intent_count,
            "error_message": job.error_message,
        }
