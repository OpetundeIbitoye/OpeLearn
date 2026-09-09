"""Phase 1 structure, fusion, and real local retrieval acceptance tests."""

import asyncio
import uuid

import pytest
from sqlalchemy import delete

from app.corpus.chunking import chunk_blocks
from app.corpus.embedding import embed, get_model, model_manifest
from app.corpus.models import Chunk, Document
from app.corpus.schemas import Block
from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.service import search


def test_chunk_token_ceiling_and_sections():
    tokenizer = get_model().tokenizer
    blocks = [
        Block(
            text="Retrieval preserves evidence and source provenance. " * 500,
            kind="text",
            section_heading="Methods",
            page_number=2,
        ),
        Block(
            text="Results confirm the source passage.",
            kind="text",
            section_heading="Results",
            page_number=3,
        ),
    ]
    chunks = chunk_blocks(blocks, tokenizer)
    assert len(chunks) > 2
    assert all(len(tokenizer.encode(c.text, add_special_tokens=False)) <= 600 for c in chunks)
    assert chunks[-1].section_heading == "Results"
    assert chunks[-1].page_number == 3
    assert all(c.section_heading == "Methods" for c in chunks[:-1])


def test_tables_remain_whole_and_oversize_tables_raise():
    tokenizer = get_model().tokenizer
    table = "| Group | Score |\n|---|---|\n| Control | 42 |\n| Treatment | 73 |"
    block = Block(text=table, kind="table", section_heading="Results", page_number=4)
    chunks = chunk_blocks([block], tokenizer)
    assert len(chunks) == 1
    assert chunks[0].text == table
    with pytest.raises(ValueError, match="Table exceeds"):
        chunk_blocks([block.model_copy(update={"text": table * 1000})], tokenizer)


def test_fusion_independent_of_retriever_list_order():
    first, second = ["a", "b", "c"], ["c", "b", "a"]
    assert reciprocal_rank_fusion([first, second]) == reciprocal_rank_fusion([second, first])
    assert reciprocal_rank_fusion([["z"], ["a"]]) == [("a", 1 / 61), ("z", 1 / 61)]


@pytest.mark.asyncio
async def test_known_query_returns_known_chunk_in_top_five():
    text = "The violet quokka observatory measures pulsar timing with a cryogenic sapphire clock."
    vector = (await asyncio.to_thread(embed, [text]))[0]
    document_id, chunk_id = uuid.uuid4(), uuid.uuid4()
    manifest = model_manifest()
    try:
        async with SessionLocal() as session, session.begin():
            session.add(
                Document(id=document_id, filename="retrieval-test", sha256=uuid.uuid4().hex)
            )
            await session.flush()
            session.add(
                Chunk(
                    id=chunk_id,
                    document_id=document_id,
                    ordinal=0,
                    text=text,
                    section_heading="Instrumentation",
                    page_number=7,
                    token_count=len(get_model().tokenizer.encode(text, add_special_tokens=False)),
                    embedding=vector,
                    embedding_model=settings.embedding_model,
                    embedding_revision=manifest["revision"],
                )
            )
        results = await search("violet quokka observatory cryogenic sapphire clock", 10)
        assert chunk_id in [candidate.chunk_id for candidate in results[:5]]
        candidate = next(c for c in results if c.chunk_id == chunk_id)
        assert candidate.dense_rank is not None and candidate.sparse_rank is not None
        assert candidate.dense_score is not None and candidate.sparse_score > 0
        assert candidate.fused_score > 0
        assert candidate.section_heading == "Instrumentation" and candidate.page_number == 7
    finally:
        async with SessionLocal() as session, session.begin():
            await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
            await session.execute(delete(Document).where(Document.id == document_id))
