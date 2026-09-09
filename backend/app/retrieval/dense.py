"""HNSW cosine search over local half-precision vectors."""

from sqlalchemy import select

from app.corpus.models import Chunk
from app.kernel.db import SessionLocal
from app.retrieval.schemas import Candidate


async def search_dense(vector: list[float], top_k: int) -> list[Candidate]:
    distance = Chunk.embedding.cosine_distance(vector)
    statement = select(Chunk, distance.label("distance")).order_by(distance).limit(top_k)
    async with SessionLocal() as session:
        rows = (await session.execute(statement)).all()
    return [
        Candidate(
            chunk_id=row.id,
            text=row.text,
            section_heading=row.section_heading,
            page_number=row.page_number,
            dense_score=1.0 - float(score),
            dense_rank=rank,
        )
        for rank, (row, score) in enumerate(rows, 1)
    ]
