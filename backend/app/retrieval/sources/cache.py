"""Redis hot cache backed by an immutable Postgres replay record."""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.kernel.db import SessionLocal
from app.kernel.redis import redis_client
from app.retrieval.models import ExternalCache
from app.retrieval.sources.base import ExternalHit, SourceProvider

REDIS_PREFIX = "external-cache:"


def normalize_query(query: str) -> str:
    return " ".join(query.casefold().split())


def cache_key(provider: str, query: str) -> str:
    value = f"{provider}{normalize_query(query)}"
    return hashlib.sha256(value.encode()).hexdigest()


async def _load(key: str) -> Any | None:
    redis_value = await redis_client.get(f"{REDIS_PREFIX}{key}")
    if redis_value is not None:
        return json.loads(redis_value)
    async with SessionLocal() as session:
        payload = await session.scalar(
            select(ExternalCache.raw_payload).where(ExternalCache.cache_key == key)
        )
    if payload is not None:
        await redis_client.set(f"{REDIS_PREFIX}{key}", json.dumps(payload, sort_keys=True))
    return payload


async def _store(key: str, provider: str, query: str, payload: Any) -> Any:
    statement = (
        insert(ExternalCache)
        .values(
            cache_key=key,
            provider=provider,
            normalized_query=normalize_query(query),
            raw_payload=payload,
        )
        .on_conflict_do_nothing(index_elements=[ExternalCache.cache_key])
    )
    async with SessionLocal() as session, session.begin():
        await session.execute(statement)
    canonical = await _load(key)
    await redis_client.set(f"{REDIS_PREFIX}{key}", json.dumps(canonical, sort_keys=True))
    return canonical


async def cached_search(provider: SourceProvider, query: str, limit: int) -> list[ExternalHit]:
    key = cache_key(provider.name, query)
    payload = await _load(key)
    if payload is None:
        payload = await _store(key, provider.name, query, await provider.fetch(query, limit))
    return provider.parse(payload)
