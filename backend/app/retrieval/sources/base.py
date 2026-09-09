"""External source interface. Every provider returns the same shape so the
pipeline never branches on which source it is talking to."""
from abc import ABC, abstractmethod

from pydantic import BaseModel


class ExternalHit(BaseModel):
    source: str
    title: str
    url: str
    snippet: str
    full_text: str | None = None
    published: str | None = None


class SourceProvider(ABC):
    name: str

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[ExternalHit]: ...
