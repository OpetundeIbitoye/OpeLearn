"""Boundaries for deterministic scaffold trigger evaluation."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ScaffoldKind(StrEnum):
    QUERY_REFINEMENT = "query_refinement"
    SOURCE_COMPARISON = "source_comparison"
    END_REFLECTION = "end_reflection"


class ScaffoldPrompt(BaseModel):
    kind: ScaffoldKind
    prompt: str


class TriggerContext(BaseModel):
    top_rerank_score: float | None = None
    disagreeing_source_count: int = Field(default=0, ge=0)
    session_ended: bool = False
