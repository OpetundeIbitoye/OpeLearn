"""Reciprocal rank fusion.

Deliberately hand-written and dependency-free: the weights are part of the
retrieval-assistance manipulation and must stay visible and loggable.
"""
from collections import defaultdict
from collections.abc import Iterable, Sequence


def reciprocal_rank_fusion(
    ranked_lists: Iterable[Sequence[str]],
    k: int = 60,
    weights: Sequence[float] | None = None,
) -> list[tuple[str, float]]:
    """Fuse ranked ID lists. Returns [(id, score), ...] best first."""
    lists = list(ranked_lists)
    w = list(weights) if weights else [1.0] * len(lists)
    scores: dict[str, float] = defaultdict(float)
    for weight, ids in zip(w, lists, strict=True):
        for rank, doc_id in enumerate(ids, start=1):
            scores[doc_id] += weight / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
