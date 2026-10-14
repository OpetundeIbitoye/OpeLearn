"""Golden manipulation checks for all three prompt modes."""

import uuid

from app.conditions.loader import load_arms
from app.conditions.schemas import ArmId
from app.retrieval.schemas import Candidate
from app.synthesis.prompts import render_prompt


def test_prompt_modes_match_declared_support() -> None:
    config = load_arms("config/arms.yaml")
    chunks = [
        Candidate(
            chunk_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            text="The fixed evidence passage was published in 2024.",
            section_heading="Findings",
            page_number=2,
        )
    ]
    rendered = {
        arm_id: render_prompt("What follows?", chunks, config.get(arm_id))[0] for arm_id in ArmId
    }

    assert len(set(rendered.values())) == len(ArmId)
    assert "Do not synthesize an answer" in rendered[ArmId.A1]
    assert "Socratic question" in rendered[ArmId.A1]
    assert "reasoned answer" in rendered[ArmId.A2]
    assert "passage displays" not in rendered[ArmId.A2]
    assert "bottom line" in rendered[ArmId.A3]
    assert "relevance and recency annotations" in rendered[ArmId.A3]
