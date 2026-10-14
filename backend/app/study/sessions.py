"""Study session lifecycle."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.kernel.db import SessionLocal
from app.study.models import Participant, StudySession


async def start_session(participant_id: uuid.UUID) -> tuple[StudySession, int]:
    """Start the phase dictated by assignment state, never by client input."""

    async with SessionLocal() as session, session.begin():
        participant = await session.scalar(
            select(Participant).where(Participant.id == participant_id).with_for_update()
        )
        if participant is None:
            raise ValueError("Unknown participant")
        completed_baseline_tasks = int(
            await session.scalar(
                select(func.count(StudySession.id)).where(
                    StudySession.participant_id == participant_id,
                    StudySession.phase == "baseline",
                    StudySession.ended_at.is_not(None),
                )
            )
            or 0
        )
        phase = "baseline" if participant.baseline_cluster is None else "treatment"
        study_session = StudySession(id=uuid.uuid4(), participant_id=participant_id, phase=phase)
        session.add(study_session)
    return study_session, completed_baseline_tasks


async def end_session(session_id: uuid.UUID, participant_id: uuid.UUID) -> None:
    async with SessionLocal() as session, session.begin():
        study_session = await session.scalar(
            select(StudySession).where(
                StudySession.id == session_id,
                StudySession.participant_id == participant_id,
            )
        )
        if study_session is None:
            raise ValueError("Unknown session")
        if study_session.ended_at is None:
            study_session.ended_at = datetime.now(UTC)
