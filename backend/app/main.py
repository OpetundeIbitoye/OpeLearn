"""Phase 0 service startup and health endpoint."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.conditions.loader import load_arms
from app.kernel.config import settings
from app.kernel.db import engine
from app.kernel.logging import configure_logging
from app.kernel.redis import redis_client
from app.retrieval.router import router as retrieval_router


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


app.include_router(retrieval_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "arms_hash": app.state.arms.content_hash}
