"""Semantic Scholar academic search provider."""

from typing import Any

import httpx

from app.kernel.config import settings
from app.retrieval.sources.base import ExternalHit, SourceProvider


class SemanticScholarProvider(SourceProvider):
    name = "semantic_scholar"

    async def fetch(self, query: str, limit: int = 10) -> Any:
        headers = (
            {"x-api-key": settings.semantic_scholar_key} if settings.semantic_scholar_key else {}
        )
        params = {"query": query, "limit": limit, "fields": "title,url,abstract,year"}
        async with httpx.AsyncClient(timeout=settings.external_provider_timeout_seconds) as client:
            response = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    def parse(self, payload: Any) -> list[ExternalHit]:
        return [
            ExternalHit(
                source=self.name,
                title=item.get("title") or "Untitled",
                url=item.get("url") or "",
                snippet=item.get("abstract") or "",
                published=str(item["year"]) if item.get("year") else None,
            )
            for item in payload.get("data", [])
        ]
