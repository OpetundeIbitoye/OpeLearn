"""Permanent external retrieval payloads used for exact replay."""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.kernel.db import Base


class ExternalCache(Base):
    __tablename__ = "external_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[object] = mapped_column(JSONB, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
