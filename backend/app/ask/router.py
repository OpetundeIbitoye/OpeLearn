"""POST /ask streams one A2 grounded answer."""

import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.ask.pipeline import run_turn
from app.ask.schemas import AskRequest
from app.conditions.registry import affordances, resolve_active_arm
from app.conditions.schemas import ArmId
from app.kernel.config import settings
from app.kernel.db import SessionLocal
from app.study.models import StudySession
from app.synthesis.providers.anthropic import AnthropicProvider
from app.synthesis.streaming import sse_frame

router = APIRouter(tags=["ask"])


@router.post("/ask")
async def ask(payload: AskRequest, request: Request, arm: ArmId | None = None) -> StreamingResponse:
    arms = request.app.state.arms
    if arm is not None and settings.study_phase != "development":
        raise HTTPException(status_code=404)
    try:
        session_id = uuid.UUID(request.headers.get("x-session-id", ""))
    except ValueError as error:
        raise HTTPException(status_code=422, detail="A valid x-session-id is required") from error
    async with SessionLocal() as database:
        study_session = await database.scalar(
            select(StudySession).where(
                StudySession.id == session_id,
                StudySession.participant_id == request.state.participant.id,
                StudySession.ended_at.is_(None),
            )
        )
    if study_session is None:
        raise HTTPException(status_code=403, detail="Active session required")
    assigned_arm = (
        ArmId(request.state.participant.assigned_arm)
        if study_session.phase == "treatment" and request.state.participant.assigned_arm
        else None
    )
    active_arm = resolve_active_arm(arms, assigned_arm=assigned_arm, forced_arm=arm)

    async def stream() -> AsyncIterator[str]:
        try:
            provider = AnthropicProvider()
            async for frame in run_turn(
                payload.query.strip(), active_arm, arms.content_hash, provider, session_id
            ):
                yield frame
        except (RuntimeError, ValueError) as error:
            yield sse_frame("error", {"message": str(error)})

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
    )


@router.get("/conditions/affordances")
async def get_affordances(request: Request, arm: ArmId | None = None) -> dict[str, object]:
    if arm is not None and settings.study_phase != "development":
        raise HTTPException(status_code=404)
    assigned_arm = (
        ArmId(request.state.participant.assigned_arm)
        if request.state.participant.assigned_arm
        else None
    )
    active_arm = resolve_active_arm(
        request.app.state.arms, assigned_arm=assigned_arm, forced_arm=arm
    )
    return {"affordances": affordances(active_arm)}
