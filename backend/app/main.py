from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import auth
from app.database import engine, Base
from contextlib import asynccontextmanager

from app.middleware import gateway_middleware
from app.exceptions import (
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # For dev/test, just create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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

@app.get("/health")
def health_check():
    return {"status": "ok"}
