"""Development-only local search endpoint."""

from fastapi import APIRouter, HTTPException, Request

from app.conditions.registry import resolve_active_arm
from app.conditions.schemas import ArmId
from app.kernel.config import settings
from app.retrieval.schemas import SearchRequest, SearchResponse

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest, http_request: Request, arm: ArmId | None = None
) -> SearchResponse:
    if settings.study_phase != "development":
        raise HTTPException(status_code=404)
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be blank")
    from app.retrieval.service import search as retrieve

    active_arm = resolve_active_arm(http_request.app.state.arms, forced_arm=arm)
    return await retrieve(request.query, active_arm)
