"""Prompt selection is driven only by the active arm's answer properties."""

from app.conditions.schemas import Arm
from app.retrieval.schemas import Candidate
from app.synthesis.prompts import render_prompt


def assemble_prompt(query: str, chunks: list[Candidate], arm: Arm) -> tuple[str, str]:
    return render_prompt(query, chunks, arm)
