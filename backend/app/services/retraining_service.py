"""Role-pack scoped retraining jobs (Slice 10)."""
import asyncio, json, logging, time, uuid
from datetime import datetime, timezone
from typing import Any
import httpx
from sqlalchemy import update
from sqlalchemy.future import select
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.intent import Intent
from app.models.training_phrase import TrainingPhrase

log=logging.getLogger(__name__)
JOBS: dict[str,dict[str,Any]]={}
LOCK=asyncio.Lock()
URLS={"hr":settings.RASA_HR_URL,"it":settings.RASA_IT_URL,"admissions":settings.RASA_ADMISSIONS_URL}
def now(): return datetime.now(timezone.utc).isoformat()

async def load_rows(pack):
 async with AsyncSessionLocal() as db:
  result=await db.execute(select(Intent).where(Intent.role_pack==pack).order_by(Intent.name))
  intents=list(result.scalars().all()); rows=[]; dirty=[]
  for i in intents:
   p=await db.execute(select(TrainingPhrase.phrase_text).where(TrainingPhrase.intent_id==i.intent_id).order_by(TrainingPhrase.created_at))
   phrases=[r[0].strip() for r in p.all() if r[0] and r[0].strip()]
   rows.append({"name":i.name,"examples":phrases})
   if i.needs_retrain: dirty.append(i.intent_id)
  return rows,dirty

async def train(pack, rows):
 async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=5)) as c:
  if pack=="it":
   r=await c.post(URLS[pack].rstrip()+"/internal/retrain",
     json={"examples_by_intent":{x["name"]:x["examples"] for x in rows if x["examples"]}},
     headers={"X-Vario-Internal-Token":settings.RETRAINING_INTERNAL_TOKEN})
   r.raise_for_status(); return
  # Rasa's model API is used for real training and reload, not a simulated success.
  nlu={"version":"3.1","nlu":[{"intent":x["name"],"examples":"\\n".join("- "+p for p in x["examples"])} for x in rows if x["examples"]]}
  import yaml, io, zipfile
  archive=io.BytesIO()
  with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as z: z.writestr("data/nlu.yml",yaml.safe_dump(nlu,sort_keys=False,allow_unicode=True))
  config="recipe: default.v1\nlanguage: en\npipeline:\n  - name: WhitespaceTokenizer\n  - name: CountVectorsFeaturizer\n  - name: DIETClassifier\n    epochs: 30\n"
  domain="version: \"3.1\"\nintents:\n"+"".join("  - "+x["name"]+"\n" for x in rows if x["examples"])+"  - nlu_fallback\n"
  r=await c.post(URLS[pack].rstrip()+"/model/train",data={"config":config,"domain":domain,"save_to_default_model_directory":"true"},files={"training_files":("training-data.zip",archive.getvalue(),"application/zip")})
  r.raise_for_status()
  r=await c.post(URLS[pack].rstrip()+"/model/reload"); r.raise_for_status()

async def run(job_id,pack):
 async with LOCK: JOBS[job_id].update(state="training",started_at=now())
 try:
  rows,dirty=await load_rows(pack)
  if not rows: raise RuntimeError("No intents are configured for this role pack")
  await train(pack,rows)
  if dirty:
   async with AsyncSessionLocal() as db:
    await db.execute(update(Intent).where(Intent.role_pack==pack,Intent.intent_id.in_(dirty)).values(needs_retrain=False)); await db.commit()
  async with LOCK: JOBS[job_id].update(state="complete",completed_at=now(),intent_count=len(rows),error_message=None)
 except Exception as exc:
  log.exception("Retraining job failed: %s",job_id)
  async with LOCK: JOBS[job_id].update(state="failed",completed_at=now(),error_message=f"Retraining failed ({type(exc).__name__}); check service logs.")

async def create_job(pack,actor):
 async with LOCK:
  if any(j["role_pack"]==pack and j["state"] in ("pending","training") for j in JOBS.values()): raise ValueError("A retraining job is already running for this role pack.")
  jid=str(uuid.uuid4()); JOBS[jid]={"job_id":jid,"role_pack":pack,"actor_id":actor,"state":"pending","created_at":now(),"started_at":None,"completed_at":None,"error_message":None,"created_epoch":time.time()}
 asyncio.create_task(run(jid,pack)); return {"retrain_job_id":jid}
async def get_job(jid,pack):
 async with LOCK:
  j=JOBS.get(jid)
  return {k:v for k,v in j.items() if k not in ("actor_id","created_epoch")} if j and j["role_pack"]==pack else None
