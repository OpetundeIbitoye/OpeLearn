"""Postgres full-text retrieval. ts_rank is not true BM25."""

from sqlalchemy import func, select

from app.corpus.models import Chunk
from app.kernel.db import SessionLocal
from app.retrieval.schemas import Candidate


async def search_sparse(query: str, top_k: int) -> list[Candidate]:
    terms = func.plainto_tsquery("english", query)
    score = func.ts_rank(Chunk.search_vector, terms)
    statement = (
        select(Chunk, score)
        .where(Chunk.search_vector.op("@@")(terms))
        .order_by(score.desc(), Chunk.id)
        .limit(top_k)
    )
    async with SessionLocal() as session:
        rows = (await session.execute(statement)).all()
    return [
        Candidate(
            chunk_id=row.id,
            text=row.text,
            section_heading=row.section_heading,
            page_number=row.page_number,
            sparse_score=float(value),
            sparse_rank=rank,
        )
        for rank, (row, value) in enumerate(rows, 1)
    ]
