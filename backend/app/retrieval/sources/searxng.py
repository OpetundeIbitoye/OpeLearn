"""JSON client for the local SearXNG service."""

from typing import Any

import httpx

from app.kernel.config import settings
from app.retrieval.sources.base import ExternalHit, SourceProvider


class SearxngProvider(SourceProvider):
    name = "searxng"

    async def fetch(self, query: str, limit: int = 10) -> Any:
        async with httpx.AsyncClient(timeout=settings.external_provider_timeout_seconds) as client:
            response = await client.get(
                f"{settings.searxng_url.rstrip('/')}/search",
                params={"q": query, "format": "json"},
            )
            response.raise_for_status()
            payload = response.json()
            payload["results"] = payload.get("results", [])[:limit]
            return payload

    def parse(self, payload: Any) -> list[ExternalHit]:
        return [
            ExternalHit(
                source=self.name,
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                snippet=item.get("content") or "",
                published=item.get("publishedDate"),
            )
            for item in payload.get("results", [])
        ]
