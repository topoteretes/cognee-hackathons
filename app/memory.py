from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import suppress
from typing import Any

import redis

from .models import HtmlDocument


class RedisSessionMemory:
    """Small Redis-backed session scratchpad for raw events and feedback."""

    def __init__(self, url: str | None = None, prefix: str = "askvio-wiki") -> None:
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.prefix = prefix
        self._client: redis.Redis | None = None
        with suppress(Exception):
            self._client = redis.Redis.from_url(self.url, decode_responses=True)
            self._client.ping()

    @property
    def available(self) -> bool:
        return self._client is not None

    def event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        if not self._client:
            return
        record = {"ts": time.time(), "type": event_type, "payload": payload}
        key = f"{self.prefix}:session:{session_id}:events"
        try:
            self._client.rpush(key, json.dumps(record))
            self._client.ltrim(key, -200, -1)
        except redis.RedisError:
            self._client = None

    def recent(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._client:
            return []
        key = f"{self.prefix}:session:{session_id}:events"
        try:
            values = self._client.lrange(key, max(0, -limit), -1)
        except redis.RedisError:
            self._client = None
            return []
        return [json.loads(value) for value in values]


class CogneePermanentMemory:
    """Optional adapter that mirrors wiki distillation into Cognee when configured."""

    def __init__(self) -> None:
        self.enabled = os.getenv("ENABLE_COGNEE", "0") == "1"
        self.last_error: str | None = None

    async def remember_documents(self, documents: list[HtmlDocument]) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "remembered": 0, "message": "Set ENABLE_COGNEE=1 to mirror distilled wiki pages into Cognee."}
        try:
            import cognee

            remembered = 0
            for doc in documents:
                content = f"# {doc.title}\n\n" + "\n\n".join(
                    f"## {section['heading']}\n{section['text']}" for section in doc.sections
                )
                maybe_awaitable = cognee.remember(content)
                if asyncio.iscoroutine(maybe_awaitable):
                    await maybe_awaitable
                remembered += 1
            return {"enabled": True, "remembered": remembered, "message": "Distilled pages mirrored to Cognee permanent memory."}
        except Exception as exc:  # pragma: no cover - depends on external service/config
            self.last_error = str(exc)
            return {"enabled": True, "remembered": 0, "error": self.last_error}
