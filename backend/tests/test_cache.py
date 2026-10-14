"""External retrieval cache replay and provider failure isolation."""

from typing import Any

import pytest

from app.retrieval import service
from app.retrieval.sources import cache
from app.retrieval.sources.base import ExternalHit, SourceProvider


class FakeProvider(SourceProvider):
    name = "fake"

    def __init__(self, *, fails: bool = False) -> None:
        self.calls = 0
        self.fails = fails

    async def fetch(self, query: str, limit: int = 10) -> Any:
        self.calls += 1
        if self.fails:
            raise RuntimeError("provider unavailable")
        return {"query": query, "results": [{"title": "Stable result"}]}

    def parse(self, payload: Any) -> list[ExternalHit]:
        return [
            ExternalHit(
                source=self.name,
                title=item["title"],
                url="https://example.test/result",
                snippet=payload["query"],
            )
            for item in payload["results"]
        ]


@pytest.mark.asyncio
async def test_identical_normalized_queries_replay_cached_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored: dict[str, Any] = {}

    async def fake_load(key: str) -> Any | None:
        return stored.get(key)

    async def fake_store(key: str, provider: str, query: str, payload: Any) -> Any:
        stored[key] = payload
        return payload

    monkeypatch.setattr(cache, "_load", fake_load)
    monkeypatch.setattr(cache, "_store", fake_store)
    provider = FakeProvider()

    first = await cache.cached_search(provider, " Transformer   Attention ", 10)
    second = await cache.cached_search(provider, "transformer attention", 10)

    assert first == second
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_provider_exception_is_skipped() -> None:
    assert await service._external(FakeProvider(fails=True), "query", 10) == []
