"""The rendered string and its hash describe the exact provider input."""

import hashlib
import uuid

from app.retrieval.schemas import Candidate
from app.synthesis.prompts import render_a2_prompt


def test_a2_prompt_is_stable_and_hashed_after_rendering() -> None:
    chunks = [
        Candidate(
            chunk_id=uuid.uuid4(),
            text="Evidence passage.",
            section_heading="Findings",
            page_number=2,
        )
    ]
    first, first_hash = render_a2_prompt("What follows?", chunks)
    second, second_hash = render_a2_prompt("What follows?", chunks)
    assert first == second
    assert first_hash == second_hash == hashlib.sha256(first.encode()).hexdigest()
    assert "[1] Evidence passage." in first
    assert "reasoned answer" in first
