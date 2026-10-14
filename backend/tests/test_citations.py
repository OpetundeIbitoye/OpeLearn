"""Citation markers must resolve to context positions and exact chunk IDs."""

import uuid

import pytest

from app.retrieval.schemas import Candidate
from app.synthesis.citations import CitationResolutionError, resolve_citations


def candidate() -> Candidate:
    return Candidate(
        chunk_id=uuid.uuid4(), text="passage", section_heading="Section", page_number=1
    )


def test_third_marker_resolves_to_third_context_chunk() -> None:
    context = [candidate(), candidate(), candidate()]
    resolved = resolve_citations("The result follows from the evidence [3].", context)
    assert len(resolved) == 1
    assert resolved[0].marker == 3
    assert resolved[0].chunk_id == context[2].chunk_id


def test_unresolvable_marker_raises() -> None:
    with pytest.raises(CitationResolutionError, match=r"Citation \[3\]"):
        resolve_citations("Unsupported claim [3].", [candidate(), candidate()])


def test_answer_without_citations_raises() -> None:
    with pytest.raises(CitationResolutionError, match="contains no citations"):
        resolve_citations("Unsupported uncited answer.", [candidate()])
