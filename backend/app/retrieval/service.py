"""Concurrent local and external retrieval with failure isolation."""

import asyncio
import re

import httpx
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.conditions.schemas import Arm
from app.corpus.embedding import embed
from app.kernel.config import settings
from app.kernel.logging import log
from app.retrieval.dense import search_dense
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.rerank import rerank
from app.retrieval.schemas import Candidate, SearchResponse
from app.retrieval.sources.base import ExternalHit, SourceProvider
from app.retrieval.sources.cache import cached_search
from app.retrieval.sources.openalex import OpenAlexProvider
from app.retrieval.sources.searxng import SearxngProvider
from app.retrieval.sources.semantic_scholar import SemanticScholarProvider
from app.retrieval.sparse import search_sparse

PROVIDERS: tuple[SourceProvider, ...] = (
    OpenAlexProvider(),
    SemanticScholarProvider(),
    SearxngProvider(),
)


async def search_corpus(query: str, top_k: int) -> list[Candidate]:
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


async def _external(provider: SourceProvider, query: str, top_k: int) -> list[ExternalHit]:
    try:
        return await asyncio.wait_for(
            cached_search(provider, query, top_k),
            timeout=settings.external_provider_timeout_seconds,
        )
    except (
        httpx.HTTPError,
        OSError,
        RedisError,
        RuntimeError,
        SQLAlchemyError,
        TimeoutError,
        ValueError,
    ) as error:
        log.warning("external_retrieval_failed", provider=provider.name, error=str(error))
        return []


def _query_plan(query: str, arm: Arm) -> tuple[list[str], list[str]]:
    original = " ".join(query.split())
    rewritten = re.sub(r"[^\w\s-]", " ", original).casefold()
    rewritten = " ".join(rewritten.split())
    primary = rewritten if arm.retrieval.rewrite_query else original
    variants = [original]
    if primary != original:
        variants.append(primary)
    searches = [primary]
    if arm.retrieval.decompose:
        parts = [part.strip() for part in re.split(r"\band\b|[;?]", primary) if part.strip()]
        searches.extend(part for part in parts if part not in searches)
        variants.extend(part for part in parts if part not in variants)
    suffixes = ("research evidence", "recent scholarly evidence")
    while len(searches) < arm.retrieval.passes:
        expanded = f"{primary} {suffixes[(len(searches) - 1) % len(suffixes)]}"
        searches.append(expanded)
        if expanded not in variants:
            variants.append(expanded)
    return variants, searches[: arm.retrieval.passes]


async def search(query: str, arm: Arm) -> SearchResponse:
    if not query.strip():
        raise ValueError("Query must not be blank")
    variants, searches = _query_plan(query, arm)
    results = await asyncio.gather(
        *(search_corpus(variant, arm.retrieval.top_k) for variant in searches),
        *(
            _external(provider, variant, arm.retrieval.top_k)
            for variant in searches
            for provider in PROVIDERS
        ),
    )
    corpus_groups = results[: len(searches)]
    external_groups = results[len(searches) :]
    corpus_by_id: dict[str, Candidate] = {}
    for group in corpus_groups:
        for candidate in group:
            key = str(candidate.chunk_id)
            current = corpus_by_id.get(key)
            if current is None or candidate.fused_score > current.fused_score:
                corpus_by_id[key] = candidate
    corpus = sorted(corpus_by_id.values(), key=lambda item: item.fused_score, reverse=True)
    if arm.retrieval.rerank:
        corpus = await rerank(searches[0], corpus, arm.retrieval.top_k)
    else:
        corpus = corpus[: arm.retrieval.top_k]
    external_by_key: dict[tuple[str, str], ExternalHit] = {}
    for group in external_groups:
        for hit in group:
            external_by_key.setdefault((hit.source, hit.url), hit)
    return SearchResponse(
        query_variants=variants,
        corpus=corpus,
        external=list(external_by_key.values()),
    )
