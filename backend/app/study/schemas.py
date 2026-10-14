"""Validated study HTTP boundaries."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ParticipantCreated(BaseModel):
    participant_id: uuid.UUID
    pseudonym: str


class ConsentRecord(BaseModel):
    participant_id: uuid.UUID
    version: str
    accepted: bool


class SessionCreate(BaseModel):
    participant_id: uuid.UUID


class SessionView(BaseModel):
    session_id: uuid.UUID
    phase: str
    baseline_tasks_completed: int
    baseline_tasks_required: int
    assignment_eligible: bool


class EventInput(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    event_type: str = Field(min_length=1, max_length=100)
    payload: dict[str, Any] = Field(default_factory=dict)
    client_timestamp: datetime


class EventBatch(BaseModel):
    session_id: uuid.UUID
    events: list[EventInput] = Field(min_length=1, max_length=500)


class SurveySubmission(BaseModel):
    session_id: uuid.UUID
    instrument: str
    trigger: Literal["post_task", "post_session", "baseline"]
    responses: dict[str, int | float | str]
