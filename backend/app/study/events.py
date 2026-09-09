"""The study event log. Append-only. This is research data, not telemetry.

Distinct from kernel/logging.py: application logs may be discarded, these
may not. Different table, different retention, different backup policy.
"""
from pydantic import BaseModel


class FreezeList(BaseModel):
    """Recorded on every single turn. If any of these differ across
    participants, the study has a problem that analysis cannot fix."""

    embedding_model: str
    reranker_model: str
    generation_model: str
    arms_hash: str


# TODO: SQLAlchemy models for
#   participant, session, turn, retrieval_result,
#   interaction_event, survey_response, external_cache
