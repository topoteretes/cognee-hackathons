"""Slack bot that recalls gtm-brain context for new channel messages."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from .cognee_client import connect, recall, write
from .env import load_project_env
from .normalize import Doc, Utterance
from .sources.slack import SlackSource, channels_from_env

log = logging.getLogger(__name__)

_ISSUE_CONTEXT_TERMS = (
    "issue",
    "issues",
    "bug",
    "bugs",
    "problem",
    "problems",
    "error",
    "errors",
    "fail",
    "fails",
    "failing",
    "failure",
    "broken",
    "regression",
    "doesn't work",
    "does not work",
    "not working",
    "stuck",
    "blocked",
    "trouble",
    "help",
)
_GENERIC_QUERY_TERMS = {
    "about",
    "any",
    "are",
    "blocked",
    "broken",
    "bug",
    "bugs",
    "doesn",
    "error",
    "errors",
    "fail",
    "failing",
    "fails",
    "failure",
    "good",
    "had",
    "having",
    "help",
    "issue",
    "issues",
    "known",
    "morning",
    "people",
    "problem",
    "problems",
    "recent",
    "regression",
    "some",
    "stuck",
    "there",
    "trouble",
    "what",
    "when",
    "with",
    "work",
    "working",
}
_QUESTION_START_TERMS = {
    "can",
    "could",
    "did",
    "do",
    "does",
    "has",
    "have",
    "how",
    "is",
    "should",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "whom",
    "whose",
    "why",
    "would",
}


def _app_token() -> str:
    token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SLACK_APP_TOKEN is required for Socket Mode")
    return token


def _bot_token() -> str:
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SLACK_BOT_TOKEN is required")
    return token


def _reply_channels() -> set[str]:
    raw = os.environ.get("SLACK_BOT_CHANNELS", "").strip()
    if raw:
        return {channel.strip() for channel in raw.split(",") if channel.strip()}
    return set(channels_from_env())


def _skip_reason(event: dict[str, Any], allowed_channels: set[str], bot_user_id: str) -> str | None:
    if event.get("type") != "message":
        return f"unsupported event type {event.get('type')!r}"
    if event.get("subtype"):
        return f"message subtype {event.get('subtype')!r}"
    if event.get("bot_id") or event.get("user") == bot_user_id:
        return "bot/self message"
    if not (event.get("text") or "").strip():
        return "empty text"
    if allowed_channels and event.get("channel") not in allowed_channels:
        return f"channel {event.get('channel')!r} not in allowlist"
    if _respond_to_all_channel_messages():
        return None
    if _mentions_bot(event.get("text") or "", bot_user_id):
        return None
    if _looks_like_question(event.get("text") or ""):
        return None
    if not _has_issue_context(event.get("text") or ""):
        return "no mention or issue context"
    return None


def _input_skip_reason(event: dict[str, Any], allowed_channels: set[str], bot_user_id: str) -> str | None:
    if event.get("type") != "message":
        return f"unsupported event type {event.get('type')!r}"
    if event.get("subtype"):
        return f"message subtype {event.get('subtype')!r}"
    if event.get("bot_id") or event.get("user") == bot_user_id:
        return "bot/self message"
    if not (event.get("text") or "").strip():
        return "empty text"
    if allowed_channels and event.get("channel") not in allowed_channels:
        return f"channel {event.get('channel')!r} not in allowlist"
    return None


def _should_reply(event: dict[str, Any], allowed_channels: set[str], bot_user_id: str) -> bool:
    return _skip_reason(event, allowed_channels, bot_user_id) is None


def _top_k() -> int:
    try:
        return max(1, int(os.environ.get("SLACK_BOT_RECALL_TOP_K", "3")))
    except ValueError:
        return 3


def _respond_to_all_channel_messages() -> bool:
    return os.environ.get("SLACKBOT_RESPOND_TO_ALL", "").lower() in ("1", "true", "yes")


def _recall_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.environ.get("SLACK_BOT_RECALL_TIMEOUT", "45")))
    except ValueError:
        return 45.0


_cognee_lock = asyncio.Lock()


def _log_background_task_result(task: asyncio.Task[None], label: str) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        log.info("slackbot: background %s cancelled", label)
    except Exception:
        log.exception("slackbot: background %s failed", label)


def _process_event_in_background(
    *,
    web_client: AsyncWebClient,
    slack_source: SlackSource,
    event: dict[str, Any],
    allowed_channels: set[str],
    bot_user_id: str,
) -> None:
    task = asyncio.create_task(
        _process_event(
            web_client=web_client,
            slack_source=slack_source,
            event=dict(event),
            allowed_channels=set(allowed_channels),
            bot_user_id=bot_user_id,
        )
    )
    task.add_done_callback(lambda done: _log_background_task_result(done, "event-processing"))


def _has_issue_context(text: str) -> bool:
    normalized = text.lower()
    return any(term in normalized for term in _ISSUE_CONTEXT_TERMS)


def _mentions_bot(text: str, bot_user_id: str) -> bool:
    return f"<@{bot_user_id}>" in text


def _remember_command_text(text: str, bot_user_id: str) -> str | None:
    if not _mentions_bot(text, bot_user_id):
        return None
    match = re.search(r"\bremember\s*:\s*(.+)", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    remembered = match.group(1).strip()
    return remembered or None


def _looks_like_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    match = re.match(r"(?:<@[A-Z0-9]+>\s*)?([a-zA-Z]+)", stripped)
    return bool(match and match.group(1).lower() in _QUESTION_START_TERMS)


def _format_recall_response(results: list[Any]) -> str | None:
    if not results:
        return None

    lines = ["Here is what I found in company brain:"]
    for index, result in enumerate(results[:3], start=1):
        text = _result_text(result)
        if text:
            lines.append(f"{index}. {text}")
    if len(lines) == 1:
        return None
    return "\n".join(lines)


def _has_relevant_context(query: str, results: list[Any]) -> bool:
    if not results:
        return False

    query_terms = _specific_terms(query)
    if not query_terms:
        return True

    context = " ".join(_result_text(result).lower() for result in results)
    context_terms = {_normalize_term(term) for term in re.findall(r"[a-z0-9]+", context)}
    return bool(query_terms & context_terms)


def _specific_terms(text: str) -> set[str]:
    terms: set[str] = set()
    for term in re.findall(r"[a-z0-9]+", text.lower()):
        normalized = _normalize_term(term)
        if len(normalized) >= 4 and normalized not in _GENERIC_QUERY_TERMS:
            terms.add(normalized)
    return terms


def _normalize_term(term: str) -> str:
    if len(term) > 4 and term.endswith("ing"):
        return term[:-3]
    if len(term) > 3 and term.endswith("s"):
        return term[:-1]
    return term


def _result_text(result: Any) -> str:
    if isinstance(result, str):
        text = result
    elif isinstance(result, dict):
        text = (
            result.get("text")
            or result.get("content")
            or result.get("value")
            or result.get("payload")
            or str(result)
        )
    else:
        text = str(result)
    return " ".join(str(text).split())[:900]


async def _recall_with_timeout(
    query: str,
    *,
    top_k: int,
    only_context: bool = False,
) -> list[dict]:
    return await asyncio.wait_for(
        recall(query, top_k=top_k, only_context=only_context),
        timeout=_recall_timeout_seconds(),
    )


async def _reply_to_event(
    *,
    web_client: AsyncWebClient,
    event: dict[str, Any],
    allowed_channels: set[str],
    bot_user_id: str,
) -> None:
    skip_reason = _skip_reason(event, allowed_channels, bot_user_id)
    if skip_reason:
        log.info("slackbot: skipping event: %s", skip_reason)
        return

    channel = event["channel"]
    text = event["text"].strip()
    thread_ts = event.get("thread_ts") or event["ts"]
    log.info("slackbot: recalling for message %s/%s", channel, event["ts"])

    try:
        top_k = _top_k()
        context_results = await _recall_with_timeout(text, top_k=top_k, only_context=True)
        if not _has_relevant_context(text, context_results):
            log.info(
                "slackbot: no relevant graph context for message %s/%s; skipping reply",
                channel,
                event["ts"],
            )
            return
        results = await _recall_with_timeout(text, top_k=top_k)
        response = _format_recall_response(results)
    except Exception as exc:
        log.exception("slackbot: recall failed")
        response = f"I tried to search company brain, but recall failed: {type(exc).__name__}: {exc}"

    if response is None:
        log.info("slackbot: no recall results for message %s/%s; staying silent", channel, event["ts"])
        return

    await web_client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=response)


async def _remember_event(
    *,
    slack_source: SlackSource,
    event: dict[str, Any],
    text_override: str | None = None,
) -> None:
    channel = event["channel"]
    ts = event["ts"]
    thread_ts = event.get("thread_ts") or ts
    text = (text_override if text_override is not None else event.get("text") or "").strip()
    if not text:
        return

    log.info("slackbot: remember starting for message %s/%s", channel, ts)
    channel_name = await slack_source._channel_name(channel)  # noqa: SLF001
    speaker = await slack_source._user_email(event["user"]) if event.get("user") else "unknown"  # noqa: SLF001
    resolved_text = await slack_source._resolve_mentions(text)  # noqa: SLF001
    timestamp = datetime.fromtimestamp(float(ts), tz=timezone.utc)
    project = slack_source.project_map.get(channel) or slack_source.project_map.get(channel_name)
    extra_tags = ["origin:adhoc"] if channel_name == "adhoc" else []
    doc = Doc(
        source="slack",
        doc_id=thread_ts,
        title=f"#{channel_name}: {resolved_text.splitlines()[0][:80]}",
        container=channel_name,
        started_at=timestamp,
        utterances=[Utterance(speaker=speaker, timestamp=timestamp, text=resolved_text)],
        project=project,
        extra_tags=extra_tags,
    )
    await write(doc)
    log.info("slackbot: remember completed for message %s/%s", channel, ts)


async def _process_event(
    *,
    web_client: AsyncWebClient,
    slack_source: SlackSource,
    event: dict[str, Any],
    allowed_channels: set[str],
    bot_user_id: str,
) -> None:
    skip_reason = _input_skip_reason(event, allowed_channels, bot_user_id)
    if skip_reason:
        log.info("slackbot: skipping event: %s", skip_reason)
        return

    log.info("slackbot: waiting for cognee slot for message %s/%s", event["channel"], event["ts"])
    async with _cognee_lock:
        remember_text = _remember_command_text(event["text"], bot_user_id)
        if remember_text is not None:
            await _remember_event(slack_source=slack_source, event=event, text_override=remember_text)
            await web_client.chat_postMessage(
                channel=event["channel"],
                thread_ts=event.get("thread_ts") or event["ts"],
                text="Remembered in company brain.",
            )
            return

        if _should_reply(event, allowed_channels, bot_user_id):
            await _reply_to_event(
                web_client=web_client,
                event=event,
                allowed_channels=allowed_channels,
                bot_user_id=bot_user_id,
            )
        else:
            log.info("slackbot: skipping reply: no mention or issue context")


async def _handle_event(
    client: SocketModeClient,
    request: SocketModeRequest,
    *,
    web_client: AsyncWebClient,
    slack_source: SlackSource,
    allowed_channels: set[str],
    bot_user_id: str,
) -> None:
    await client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))

    if request.type != "events_api":
        log.info("slackbot: ignoring socket request type %s", request.type)
        return
    event = request.payload.get("event", {})
    log.info(
        "slackbot: received event type=%s subtype=%s channel=%s user=%s text=%r",
        event.get("type"),
        event.get("subtype"),
        event.get("channel"),
        event.get("user"),
        (event.get("text") or "")[:120],
    )

    _process_event_in_background(
        web_client=web_client,
        slack_source=slack_source,
        event=event,
        allowed_channels=allowed_channels,
        bot_user_id=bot_user_id,
    )


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    load_project_env()
    await connect()

    web_client = AsyncWebClient(token=_bot_token())
    auth = await web_client.auth_test()
    bot_user_id = auth["user_id"]
    allowed_channels = _reply_channels()
    slack_source = SlackSource()

    client = SocketModeClient(app_token=_app_token(), web_client=web_client)

    async def listener(socket_client: SocketModeClient, request: SocketModeRequest) -> None:
        await _handle_event(
            socket_client,
            request,
            web_client=web_client,
            slack_source=slack_source,
            allowed_channels=allowed_channels,
            bot_user_id=bot_user_id,
        )

    client.socket_mode_request_listeners.append(listener)
    await client.connect()
    log.info(
        "slackbot: listening as %s on %s",
        bot_user_id,
        ", ".join(sorted(allowed_channels)) if allowed_channels else "all invited channels",
    )
    await asyncio.Event().wait()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
