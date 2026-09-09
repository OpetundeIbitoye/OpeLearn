"""The LLM adapter interface.

One interface, several implementations. Swapping provider is a config change,
never an architecture change — which is what keeps the 'can student queries
leave institutional infrastructure' question from blocking the build.

Every implementation MUST report `version_string`, which is recorded on each
turn as part of the freeze list.
"""
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class GenerationProvider(ABC):
    name: str

    @property
    @abstractmethod
    def version_string(self) -> str:
        """Exact pinned model identifier, e.g. 'claude-sonnet-5'."""

    @abstractmethod
    async def stream(
        self, messages: list[Message], max_tokens: int, temperature: float = 0.0
    ) -> AsyncIterator[str]: ...
