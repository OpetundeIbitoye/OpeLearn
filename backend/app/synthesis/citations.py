"""Resolve answer markers to the exact context chunks they cite."""

import re
from uuid import UUID

from pydantic import BaseModel

from app.retrieval.schemas import Candidate

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


class CitationResolutionError(ValueError):
    pass


class ResolvedCitation(BaseModel):
    marker: int
    chunk_id: UUID


def resolve_citations(answer: str, context: list[Candidate]) -> list[ResolvedCitation]:
    resolved: list[ResolvedCitation] = []
    seen: set[int] = set()
    for match in CITATION_PATTERN.finditer(answer):
        marker = int(match.group(1))
        if marker < 1 or marker > len(context):
            raise CitationResolutionError(
                f"Citation [{marker}] cannot resolve against {len(context)} context chunks"
            )
        if marker not in seen:
            resolved.append(ResolvedCitation(marker=marker, chunk_id=context[marker - 1].chunk_id))
            seen.add(marker)
    if not resolved:
        raise CitationResolutionError("Generated answer contains no citations")
    return resolved
