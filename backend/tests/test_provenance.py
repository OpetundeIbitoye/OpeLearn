"""Every persisted turn must contain the complete freeze list."""

import pytest
from sqlalchemy import func, or_, select

from app.kernel.db import SessionLocal
from app.study.models import Turn


@pytest.mark.asyncio
async def test_every_turn_has_complete_freeze_list() -> None:
    async with SessionLocal() as session:
        missing = await session.scalar(
            select(func.count())
            .select_from(Turn)
            .where(
                or_(
                    Turn.embedding_model == "",
                    Turn.reranker_model == "",
                    Turn.generation_model == "",
                    Turn.arms_hash == "",
                )
            )
        )
    assert missing == 0
