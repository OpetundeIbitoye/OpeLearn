"""Append-only study event capture, separate from application logging."""

from pydantic import BaseModel

from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.study.models import InteractionEvent
from app.study.schemas import EventBatch


class FreezeList(BaseModel):
    embedding_model: str
    reranker_model: str
    generation_model: str
    arms_hash: str


def freeze_list(arms_hash: str) -> FreezeList:
    return FreezeList(
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model,
        generation_model=settings.generation_model,
        arms_hash=arms_hash,
    )


async def append_events(batch: EventBatch) -> int:
    async with SessionLocal() as session, session.begin():
        session.add_all(
            InteractionEvent(
                id=event.id,
                session_id=batch.session_id,
                event_type=event.event_type,
                payload=event.payload,
                client_timestamp=event.client_timestamp,
            )
            for event in batch.events
        )
    return len(batch.events)
