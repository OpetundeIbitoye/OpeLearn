"""Minimal, auditable Anthropic Messages streaming adapter."""

import json
from collections.abc import AsyncIterator

import httpx

from app.kernel.config import settings
from app.synthesis.providers.base import GenerationEvent, GenerationProvider, Message


class AnthropicProvider(GenerationProvider):
    name = "anthropic"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the configured provider")
        self._client = client or httpx.AsyncClient(timeout=60.0)
        self._owns_client = client is None

    @property
    def version_string(self) -> str:
        return settings.generation_model

    async def stream(
        self, messages: list[Message], max_tokens: int, temperature: float = 0.0
    ) -> AsyncIterator[GenerationEvent]:
        payload = {
            "model": self.version_string,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "messages": [message.model_dump() for message in messages],
        }
        headers = {
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            async with self._client.stream(
                "POST", "https://api.anthropic.com/v1/messages", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    raw = line.removeprefix("data: ")
                    if raw == "[DONE]":
                        break
                    event = json.loads(raw)
                    event_type = event.get("type")
                    if event_type == "content_block_delta":
                        text = event.get("delta", {}).get("text", "")
                        if text:
                            yield GenerationEvent(text=text)
                    elif event_type == "message_start":
                        usage = event.get("message", {}).get("usage", {})
                        yield GenerationEvent(input_tokens=usage.get("input_tokens"))
                    elif event_type == "message_delta":
                        usage = event.get("usage", {})
                        yield GenerationEvent(output_tokens=usage.get("output_tokens"))
                    elif event_type == "error":
                        raise RuntimeError(event.get("error", {}).get("message", "Anthropic error"))
        finally:
            if self._owns_client:
                await self._client.aclose()
