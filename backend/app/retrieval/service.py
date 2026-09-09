"""Local dense and sparse retrieval with complete fusion provenance."""

import asyncio

from app.corpus.embedding import embed
from app.retrieval.dense import search_dense
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.schemas import Candidate
from app.retrieval.sparse import search_sparse


async def search(query: str, top_k: int) -> list[Candidate]:
    if not query.strip():
        raise ValueError("Query must not be blank")

    async def dense() -> list[Candidate]:
        vector = (await asyncio.to_thread(embed, [query], query=True))[0]
        return await search_dense(vector, top_k)

    dense_results, sparse_results = await asyncio.gather(dense(), search_sparse(query, top_k))
    candidates: dict[str, Candidate] = {str(item.chunk_id): item for item in dense_results}
    for item in sparse_results:
        key = str(item.chunk_id)
        if key in candidates:
            candidates[key].sparse_score = item.sparse_score
            candidates[key].sparse_rank = item.sparse_rank
        else:
            candidates[key] = item
    fused = reciprocal_rank_fusion(
        [[str(c.chunk_id) for c in dense_results], [str(c.chunk_id) for c in sparse_results]]
    )
    for key, score in fused:
        candidates[key].fused_score = score
    return [candidates[key] for key, _ in fused]
