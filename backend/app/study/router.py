"""Consent, session, event, and survey endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Request

from app.kernel.config import settings
from app.study.consent import CONSENT_TEXT, CONSENT_VERSION, record_consent
from app.study.events import append_events
from app.study.participants import create_participant
from app.study.schemas import (
    ConsentRecord,
    EventBatch,
    ParticipantCreated,
    SessionCreate,
    SessionView,
    SurveySubmission,
)
from app.study.sessions import end_session, start_session
from app.study.surveys import load_instruments, save_response

router = APIRouter(prefix="/study", tags=["study"])


@router.post("/participants", response_model=ParticipantCreated)
async def enrol() -> ParticipantCreated:
    participant = await create_participant()
    return ParticipantCreated(participant_id=participant.id, pseudonym=participant.pseudonym)


@router.get("/consent")
async def consent_text() -> dict[str, str]:
    return {"version": CONSENT_VERSION, "text": CONSENT_TEXT}


@router.post("/consent", status_code=204)
async def consent(payload: ConsentRecord) -> None:
    try:
        await record_consent(payload.participant_id, payload.version, payload.accepted)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.post("/sessions", response_model=SessionView)
async def create_session(payload: SessionCreate, request: Request) -> SessionView:
    if request.state.participant.id != payload.participant_id:
        raise HTTPException(status_code=403)
    try:
        session, completed = await start_session(payload.participant_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return SessionView(
        session_id=session.id,
        phase=session.phase,
        baseline_tasks_completed=completed,
        baseline_tasks_required=settings.baseline_tasks_required,
        assignment_eligible=completed >= settings.baseline_tasks_required,
    )


@router.post("/sessions/{session_id}/end", status_code=204)
async def close_session(session_id: uuid.UUID, request: Request) -> None:
    try:
        await end_session(session_id, request.state.participant.id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/events")
async def events(payload: EventBatch) -> dict[str, int]:
    return {"accepted": await append_events(payload)}


@router.get("/surveys/{trigger}")
async def surveys(trigger: str) -> list[dict[str, object]]:
    try:
        return load_instruments(trigger)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/surveys", status_code=204)
async def submit_survey(payload: SurveySubmission) -> None:
    try:
        await save_response(payload)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
