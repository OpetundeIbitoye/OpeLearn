"""OpenAlex academic search with the configured contact address."""

from typing import Any

import httpx

from app.kernel.config import settings
from app.retrieval.sources.base import ExternalHit, SourceProvider


def _abstract(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    positioned = ((position, word) for word, positions in index.items() for position in positions)
    return " ".join(word for _, word in sorted(positioned))


class OpenAlexProvider(SourceProvider):
    name = "openalex"

    async def fetch(self, query: str, limit: int = 10) -> Any:
        params = {"search": query, "per-page": limit, "mailto": settings.openalex_mailto}
        async with httpx.AsyncClient(timeout=settings.external_provider_timeout_seconds) as client:
            response = await client.get("https://api.openalex.org/works", params=params)
            response.raise_for_status()
            return response.json()

    def parse(self, payload: Any) -> list[ExternalHit]:
        return [
            ExternalHit(
                source=self.name,
                title=item.get("display_name") or "Untitled",
                url=item.get("doi") or item.get("id") or "",
                snippet=_abstract(item.get("abstract_inverted_index")),
                published=str(item["publication_year"]) if item.get("publication_year") else None,
            )
            for item in payload.get("results", [])
        ]
