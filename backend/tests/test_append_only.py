"""The database rejects mutation of study events."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.kernel.db import engine


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
async def test_study_events_are_append_only(operation: str) -> None:
    participant_id, session_id, event_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(
                text("INSERT INTO participants (id, pseudonym) VALUES (:id, :p)"),
                {"id": participant_id, "p": f"test-{participant_id}"},
            )
            await connection.execute(
                text(
                    "INSERT INTO sessions (id, participant_id, phase) VALUES (:id, :participant, 'baseline')"
                ),
                {"id": session_id, "participant": participant_id},
            )
            await connection.execute(
                text("""INSERT INTO interaction_events
                (id, session_id, event_type, payload, client_timestamp)
                VALUES (:id, :session, 'test', '{}'::jsonb, now())"""),
                {"id": event_id, "session": session_id},
            )
            statement = (
                "UPDATE interaction_events SET event_type = 'changed' WHERE id = :id"
                if operation == "UPDATE"
                else "DELETE FROM interaction_events WHERE id = :id"
            )
            with pytest.raises(DBAPIError, match="append-only"):
                await connection.execute(text(statement), {"id": event_id})
        finally:
            if transaction.is_active:
                await transaction.rollback()
