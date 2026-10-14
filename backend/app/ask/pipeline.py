"""Phase 2 A2 turn: local retrieval, prompt assembly, generation, provenance."""

import time
import uuid
from collections.abc import AsyncIterator

from app.conditions.schemas import Arm
from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.retrieval.service import search
from app.study.models import RetrievalResult, Turn
from app.synthesis.citations import resolve_citations
from app.synthesis.providers.base import GenerationProvider, Message
from app.synthesis.service import assemble_prompt
from app.synthesis.streaming import sse_frame

TEMPERATURE = 0.0


async def run_turn(
    query: str,
    arm: Arm,
    arms_hash: str,
    provider: GenerationProvider,
    session_id: uuid.UUID | None = None,
) -> AsyncIterator[str]:
    started = time.perf_counter()
    turn_id = uuid.uuid4()
    retrieval = await search(query, arm)
    context = retrieval.corpus
    if not context:
        yield sse_frame("error", {"message": "No local source passages were retrieved"})
        return
    prompt, prompt_hash = assemble_prompt(query, context, arm)
    answer_parts: list[str] = []
    input_tokens = 0
    output_tokens = 0
    try:
        async for event in provider.stream(
            [Message(role="user", content=prompt)],
            max_tokens=arm.answer.max_tokens,
            temperature=TEMPERATURE,
        ):
            if event.input_tokens is not None:
                input_tokens = event.input_tokens
            if event.output_tokens is not None:
                output_tokens = event.output_tokens
            if event.text:
                answer_parts.append(event.text)
                yield sse_frame("token", {"text": event.text})
        answer = "".join(answer_parts)
        citations = resolve_citations(answer, context)
        sources = []
        for citation in citations:
            source = context[citation.marker - 1]
            yield sse_frame(
                "citation", {"marker": citation.marker, "chunk_id": str(citation.chunk_id)}
            )
            sources.append(
                {
                    "marker": citation.marker,
                    "chunk_id": str(source.chunk_id),
                    "text": source.text,
                    "section_heading": source.section_heading,
                    "page_number": source.page_number,
                }
            )
        latency_ms = round((time.perf_counter() - started) * 1000)
        async with SessionLocal() as session, session.begin():
            session.add(
                Turn(
                    id=turn_id,
                    session_id=session_id,
                    query=query,
                    answer=answer,
                    prompt=prompt,
                    prompt_hash=prompt_hash,
                    embedding_model=settings.embedding_model,
                    reranker_model=settings.reranker_model,
                    generation_model=provider.version_string,
                    arms_hash=arms_hash,
                    temperature=TEMPERATURE,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
            session.add_all(
                RetrievalResult(
                    turn_id=turn_id,
                    chunk_id=candidate.chunk_id,
                    rank=rank,
                    dense_score=candidate.dense_score,
                    sparse_score=candidate.sparse_score,
                    fused_score=candidate.fused_score,
                    rerank_score=candidate.rerank_score,
                    query_variant=retrieval.query_variants[0],
                )
                for rank, candidate in enumerate(context, 1)
            )
        yield sse_frame("sources", {"sources": sources})
        yield sse_frame("done", {"turn_id": str(turn_id), "latency_ms": latency_ms})
    except (RuntimeError, ValueError) as error:
        yield sse_frame("error", {"message": str(error)})
