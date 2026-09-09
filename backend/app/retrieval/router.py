"""Development-only local search endpoint."""

from fastapi import APIRouter, HTTPException

from app.kernel.config import settings
from app.retrieval.schemas import Candidate, SearchRequest

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


@router.post("/search", response_model=list[Candidate])
async def search(request: SearchRequest) -> list[Candidate]:
    if settings.study_phase != "development":
        raise HTTPException(status_code=404)
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Query must not be blank")
    from app.retrieval.service import search as retrieve

    return await retrieve(request.query, request.top_k)
