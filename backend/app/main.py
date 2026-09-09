"""FastAPI entrypoint. Wires slices together; contains no domain logic."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ask.router import router as ask_router
from app.conditions.loader import load_arms
from app.corpus.router import router as corpus_router
from app.kernel.config import settings
from app.kernel.logging import configure_logging
from app.retrieval.router import router as retrieval_router
from app.study.router import router as study_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    # Fail loudly at boot if the manipulation is malformed.
    app.state.arms = load_arms(settings.arms_config)
    yield


app = FastAPI(title="Scaffolded Answer Engine", lifespan=lifespan)

app.include_router(ask_router)
app.include_router(study_router)
app.include_router(corpus_router)
app.include_router(retrieval_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "arms_hash": app.state.arms.content_hash}
