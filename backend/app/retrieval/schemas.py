"""Retrieval boundaries retain raw scores and ranks."""

from uuid import UUID

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(default=10, ge=1, le=100)


class Candidate(BaseModel):
    chunk_id: UUID
    text: str
    section_heading: str
    page_number: int
    dense_score: float | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    sparse_rank: int | None = None
    fused_score: float = 0.0
