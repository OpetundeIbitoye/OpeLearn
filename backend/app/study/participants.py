"""Create pseudonymous participants without collecting identifying data."""

import secrets
import uuid

from app.kernel.db import SessionLocal
from app.study.models import Participant


async def create_participant() -> Participant:
    participant = Participant(id=uuid.uuid4(), pseudonym=f"P-{secrets.token_hex(6).upper()}")
    async with SessionLocal() as session, session.begin():
        session.add(participant)
    return participant
