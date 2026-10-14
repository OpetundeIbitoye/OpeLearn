"""Phase 0 service startup and health endpoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.ask.router import router as ask_router
from app.conditions.loader import load_arms
from app.kernel.config import settings
from app.kernel.db import SessionLocal, engine
from app.kernel.logging import configure_logging
from app.kernel.redis import redis_client
from app.retrieval.router import router as retrieval_router
from app.study.models import Participant
from app.study.router import router as study_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    app.state.arms = load_arms(settings.arms_config)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        await redis_client.ping()
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


app = FastAPI(title="Scaffolded Answer Engine", lifespan=lifespan)

CONSENT_EXEMPT = {"/health", "/study/participants", "/study/consent"}


@app.middleware("http")
async def require_consent(request: Request, call_next):
    if request.url.path in CONSENT_EXEMPT or request.url.path.startswith(("/docs", "/openapi")):
        return await call_next(request)
    raw_participant_id = request.headers.get("x-participant-id")
    if not raw_participant_id:
        return JSONResponse(status_code=403, content={"detail": "Consent required"})
    try:
        async with SessionLocal() as session:
            participant = await session.scalar(
                select(Participant).where(Participant.id == raw_participant_id)
            )
    except (TypeError, ValueError):
        participant = None
    if participant is None or participant.consented_at is None:
        return JSONResponse(status_code=403, content={"detail": "Consent required"})
    request.state.participant = participant
    return await call_next(request)


app.include_router(ask_router)
app.include_router(retrieval_router)
app.include_router(study_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "arms_hash": app.state.arms.content_hash}
