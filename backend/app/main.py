from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import auth, conversations, chat, admin, admin_crud, retraining
from app.database import engine, Base
from app.services.retraining_service import recover_stale_jobs
from contextlib import asynccontextmanager

from app.middleware import gateway_middleware
from app.exceptions import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # SQLite (tests, quick local runs): just create tables. Anything else is owned
    # by Alembic — the container entrypoint runs `alembic upgrade head` first, and
    # create_all here would leave a schema Alembic can no longer upgrade.
    if engine.dialect.name == "sqlite":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    await recover_stale_jobs()
    yield

app = FastAPI(title="VARIO API", lifespan=lifespan)

# Exception Handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Middlewares
app.middleware("http")(gateway_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In prod, restrict this to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(admin_crud.router, prefix="/api")
app.include_router(retraining.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}

