"""Phase 2 streams incrementally and stores complete turn provenance."""

import json
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import delete, select

from app.ask import pipeline
from app.conditions.loader import load_arms
from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.retrieval.schemas import Candidate, SearchResponse
from app.study.models import Turn
from app.synthesis.providers.base import GenerationEvent, GenerationProvider, Message


class FakeProvider(GenerationProvider):
    name = "fake"

    @property
    def version_string(self) -> str:
        return settings.generation_model

    async def stream(
        self, messages: list[Message], max_tokens: int, temperature: float = 0.0
    ) -> AsyncIterator[GenerationEvent]:
        assert len(messages) == 1
        assert max_tokens == 700
        assert temperature == 0.0
        yield GenerationEvent(input_tokens=123)
        yield GenerationEvent(text="Supported ")
        yield GenerationEvent(text="answer [1].")
        yield GenerationEvent(output_tokens=7)


def decode(frame: str) -> tuple[str, dict[str, object]]:
    lines = frame.strip().splitlines()
    return lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))


@pytest.mark.asyncio
async def test_turn_streams_and_persists_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Candidate(
        chunk_id=uuid.uuid4(),
        text="Evidence passage.",
        section_heading="Findings",
        page_number=2,
        dense_score=0.9,
        sparse_score=0.8,
        dense_rank=1,
        sparse_rank=1,
        fused_score=0.03,
    )

    async def fake_search(query: str, active_arm: object) -> SearchResponse:
        assert query == "What follows?"
        assert active_arm.retrieval.top_k == 20
        return SearchResponse(query_variants=[query], corpus=[source], external=[])

    monkeypatch.setattr(pipeline, "search", fake_search)
    config = load_arms("config/arms.yaml")
    arm = config.get(config.baseline_arm)
    frames = [
        decode(frame)
        async for frame in pipeline.run_turn(
            "What follows?", arm, config.content_hash, FakeProvider()
        )
    ]
    assert [kind for kind, _ in frames] == ["token", "token", "citation", "sources", "done"]
    assert frames[0][1]["text"] == "Supported "
    assert frames[1][1]["text"] == "answer [1]."
    assert frames[2][1] == {"marker": 1, "chunk_id": str(source.chunk_id)}
    assert frames[3][1]["sources"][0]["chunk_id"] == str(source.chunk_id)
    turn_id = uuid.UUID(str(frames[-1][1]["turn_id"]))
    try:
        async with SessionLocal() as session:
            turn = await session.scalar(select(Turn).where(Turn.id == turn_id))
            assert turn is not None
            assert turn.prompt_hash and turn.prompt
            assert turn.generation_model == settings.generation_model
            assert turn.embedding_model == settings.embedding_model
            assert turn.reranker_model == settings.reranker_model
            assert turn.arms_hash == config.content_hash
            assert turn.input_tokens == 123 and turn.output_tokens == 7
            assert turn.latency_ms >= 0
    finally:
        async with SessionLocal() as session, session.begin():
            await session.execute(delete(Turn).where(Turn.id == turn_id))
