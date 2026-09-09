"""Validated parsing and chunking boundaries."""

from typing import Literal

from pydantic import BaseModel, Field


class Block(BaseModel):
    text: str
    kind: Literal["text", "table"]
    section_heading: str
    page_number: int = Field(ge=1)


class ChunkText(BaseModel):
    text: str
    section_heading: str
    page_number: int = Field(ge=1)
    token_count: int = Field(ge=1, le=600)
