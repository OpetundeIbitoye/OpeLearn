"""Locally provisioned cross-encoder reranking."""

import asyncio
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.kernel.config import settings
from app.retrieval.schemas import Candidate


@lru_cache(maxsize=1)
def _model() -> Any:
    from sentence_transformers import CrossEncoder

    path = Path(settings.model_directory) / "reranker"
    if not path.is_dir():
        raise RuntimeError(f"Provisioned reranker is missing: {path}")
    return CrossEncoder(str(path), local_files_only=True, trust_remote_code=False)


async def rerank(query: str, candidates: list[Candidate], top_k: int) -> list[Candidate]:
    if not candidates:
        return []
    scores = await asyncio.to_thread(
        _model().predict,
        [(query, candidate.text) for candidate in candidates],
        show_progress_bar=False,
    )
    for candidate, score in zip(candidates, scores, strict=True):
        candidate.rerank_score = float(score)
    return sorted(candidates, key=lambda item: item.rerank_score or float("-inf"), reverse=True)[
        :top_k
    ]
