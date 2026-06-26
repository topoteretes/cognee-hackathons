"""Slack source: pull threads from configured channels into Doc form.

Strategy: for each channel, walk recent parent messages and assemble
each thread (parent + replies) into a Doc. Bot messages are skipped.
User IDs are resolved to emails on first sight and cached for the run.
``<@U…>`` mentions in message bodies are rewritten to ``@<email>`` so
the LLM extractor sees consistent identifiers across speakers and
mentions (no more ``U012ABC…`` vs ``Alice`` vs ``alice@…`` triplets).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

from slack_sdk.web.async_client import AsyncWebClient

from ..normalize import Doc, Utterance

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]+)?>")


class SlackSource:
    def __init__(
        self,
        token: str | None = None,
        project_map: dict[str, str] | None = None,
    ) -> None:
        self.token = token or os.environ["SLACK_BOT_TOKEN"]
        self.client = AsyncWebClient(token=self.token)
        self._user_cache: dict[str, str] = {}
        self._channel_cache: dict[str, str] = {}
        self.project_map = project_map if project_map is not None else project_map_from_env()

    async def fetch_threads(self, channel_id: str, since: datetime) -> AsyncIterator[Doc]:
        """Yield one Doc per thread (or per standalone message) in channel since `since`."""
        oldest = since.timestamp()
        cursor: str | None = None
        channel_name = await self._channel_name(channel_id)

        while True:
            resp = await self.client.conversations_history(
                channel=channel_id,
                oldest=str(oldest),
                limit=200,
                cursor=cursor,
            )
            for parent in resp.get("messages", []):
                if parent.get("subtype") in {"bot_message", "channel_join", "channel_leave"}:
                    continue
                doc = await self._build_thread_doc(channel_id, channel_name, parent)
                if doc.utterances:
                    yield doc

            cursor = (resp.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break

    async def _build_thread_doc(
        self, channel_id: str, channel_name: str, parent: dict
    ) -> Doc:
        thread_ts = parent.get("thread_ts") or parent["ts"]
        messages = [parent]
        if parent.get("reply_count"):
            replies = await self.client.conversations_replies(
                channel=channel_id, ts=thread_ts, limit=200
            )
            messages = replies.get("messages", [parent])

        utterances: list[Utterance] = []
        for m in messages:
            if m.get("subtype") in {"bot_message", "channel_join", "channel_leave"}:
                continue
            text = (m.get("text") or "").strip()
            if not text:
                continue
            speaker = await self._user_email(m["user"]) if m.get("user") else "unknown"
            ts = datetime.fromtimestamp(float(m["ts"]), tz=timezone.utc)
            resolved = await self._resolve_mentions(text)
            utterances.append(Utterance(speaker=speaker, timestamp=ts, text=resolved))

        started = utterances[0].timestamp if utterances else datetime.now(timezone.utc)
        title = self._derive_title(channel_name, utterances)
        project = self.project_map.get(channel_id) or self.project_map.get(channel_name)
        extra_tags: list[str] = []
        if channel_name == "adhoc":
            extra_tags.append("origin:adhoc")
        return Doc(
            source="slack",
            doc_id=thread_ts,
            title=title,
            container=channel_name,
            started_at=started,
            utterances=utterances,
            project=project,
            extra_tags=extra_tags,
        )

    async def _resolve_mentions(self, text: str) -> str:
        """Rewrite ``<@U…>`` mentions to ``@<email>`` so they're stable across docs."""

        async def lookup(uid: str) -> str:
            return await self._user_email(uid)

        # gather unique uids first, then substitute — keeps a single
        # users.info call per uid
        uids = set(_MENTION_RE.findall(text))
        replacements: dict[str, str] = {}
        for uid in uids:
            replacements[uid] = f"@{await lookup(uid)}"
        return _MENTION_RE.sub(lambda m: replacements.get(m.group(1), m.group(0)), text)

    @staticmethod
    def _derive_title(channel_name: str, utterances: list[Utterance]) -> str:
        if not utterances:
            return f"#{channel_name} (empty)"
        snippet = utterances[0].text.splitlines()[0][:80]
        return f"#{channel_name}: {snippet}"

    async def _user_email(self, user_id: str) -> str:
        if user_id in self._user_cache:
            return self._user_cache[user_id]
        try:
            resp = await self.client.users_info(user=user_id)
            profile = resp.get("user", {}).get("profile", {})
            email = profile.get("email") or resp["user"].get("name") or user_id
        except Exception:
            log.warning("could not resolve slack user %s", user_id)
            email = user_id
        self._user_cache[user_id] = email
        return email

    async def _channel_name(self, channel_id: str) -> str:
        if channel_id in self._channel_cache:
            return self._channel_cache[channel_id]
        try:
            resp = await self.client.conversations_info(channel=channel_id)
            name = resp["channel"].get("name", channel_id)
        except Exception:
            name = channel_id
        self._channel_cache[channel_id] = name
        return name


def channels_from_env() -> list[str]:
    raw = os.environ.get("SLACK_CHANNELS", "").strip()
    return [c.strip() for c in raw.split(",") if c.strip()]


def project_map_from_env() -> dict[str, str]:
    """Parse SLACK_PROJECT_MAP into a dict.

    Format: ``CHANNEL_ID_OR_NAME:project,CHANNEL_ID:project,…``
    Channels absent from the map have no project tag — useful for shared
    spaces like an engineering channel where subtopics should emerge
    from extraction rather than be pinned to one project.
    """
    raw = os.environ.get("SLACK_PROJECT_MAP", "").strip()
    if not raw:
        return {}
    mapping: dict[str, str] = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        key, _, value = pair.partition(":")
        key, value = key.strip(), value.strip()
        if key and value:
            mapping[key] = value
    return mapping


def since_from_env() -> datetime:
    days = int(os.environ.get("INGEST_SINCE_DAYS", "30"))
    return datetime.now(timezone.utc) - timedelta(days=days)
