"""Versioned consent copy and append-once acceptance recording."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.kernel.db import SessionLocal
from app.study.models import Participant

CONSENT_VERSION = "2026-10-14-v1"
CONSENT_TEXT = """You are invited to participate in research about how students use a research answer system. Your questions, interactions, survey responses, and system outputs will be recorded for research. Participation is voluntary. You may stop at any time without penalty. Do not enter identifying or sensitive personal information."""


async def record_consent(participant_id: uuid.UUID, version: str, accepted: bool) -> None:
    if not accepted or version != CONSENT_VERSION:
        raise ValueError("Current consent must be accepted")
    async with SessionLocal() as session, session.begin():
        participant = await session.scalar(
            select(Participant).where(Participant.id == participant_id)
        )
        if participant is None:
            raise ValueError("Unknown participant")
        if participant.consented_at is None:
            participant.consent_version = version
            participant.consented_at = datetime.now(UTC)
