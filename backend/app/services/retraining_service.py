"""Role-pack scoped retraining jobs (Slice 10)."""
import io
import logging
import uuid
import zipfile
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
            rows.append({"name": intent.name, "examples": phrases})
            if intent.needs_retrain:
                dirty.append(intent.intent_id)
        return rows, dirty


def _prepare_assets(pack, rows):
    """Build one combined YAML payload accepted by Rasa 3.6's /model/train API."""
    root = Path(settings.ROLE_PACKS_DIR) / pack
    config_path, domain_path = root / "config.yml", root / "domain.yml"
    if not config_path.is_file() or not domain_path.is_file():
        raise RuntimeError(f"Training assets unavailable for {pack}; check role-pack mounts.")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    domain = yaml.safe_load(domain_path.read_text(encoding="utf-8")) or {}
    intents = domain.setdefault("intents", [])
    names = {item if isinstance(item, str) else next(iter(item), "") for item in intents}
    for row in rows:
        if row["examples"] and row["name"] not in names:
            intents.append(row["name"])

    files = {}
    data_dir = root / "data"
    if data_dir.is_dir():
        for path in data_dir.rglob("*"):
            if path.is_file() and path.suffix in (".yml", ".yaml"):
                files[path.relative_to(root).as_posix()] = path.read_text(encoding="utf-8")

    nlu = yaml.safe_load(files.get("data/nlu.yml", 'version: "3.1"\nnlu: []')) or {}
    nlu.setdefault("version", "3.1")
    replace_names = {row["name"] for row in rows}
    items = [item for item in nlu.setdefault("nlu", []) if item.get("intent") not in replace_names]
    for row in rows:
        if row["examples"]:
            items.append({
                "intent": row["name"],
                "examples": "\n".join("- " + phrase for phrase in row["examples"]),
            })
    nlu["nlu"] = items
    files["data/nlu.yml"] = yaml.safe_dump(nlu, sort_keys=False, allow_unicode=True)

    # The Rasa 3.6 HTTP training endpoint consumes a single YAML document
    # combining config, domain, and training data. Preserve multiple list-based
    # sections when the role pack has more than one file for a section.
    payload = {}
    sources = [config, domain]
    sources.extend(yaml.safe_load(value) or {} for value in files.values())
    for source in sources:
        for key, value in source.items():
            if isinstance(payload.get(key), list) and isinstance(value, list):
                payload[key].extend(value)
            elif isinstance(payload.get(key), dict) and isinstance(value, dict):
                payload[key].update(value)
            else:
                payload[key] = value
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)

async def train(pack, rows):
    """Train a role pack and activate the returned artifact through Rasa's HTTP API."""
    training_yaml = _prepare_assets(pack, rows)
    base_url = URLS[pack].rstrip()
    async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5)) as client:
        response = await client.post(
            base_url + "/model/train?save_to_default_model_directory=true",
            content=training_yaml,
            headers={"Content-Type": "application/x-yaml"},
        )
        response.raise_for_status()

        # Rasa 3.6 saves the archive in its default models directory and returns
        # its filename. Activate that exact artifact through PUT /model.
        filename = response.headers.get("filename", "")
        if not filename or Path(filename).name != filename:
            raise RuntimeError("Rasa training response did not include a valid model filename.")
        response = await client.put(base_url + "/model", json={"model_file": f"models/{filename}"})
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
