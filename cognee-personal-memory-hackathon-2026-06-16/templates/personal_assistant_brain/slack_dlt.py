"""Adapters from dlt's verified Slack source to Cognee Docs."""

from __future__ import annotations

import logging
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import Iterable, Iterator

from company_brain.normalize import Doc, Utterance

try:
    import dlt  # noqa: F401

    from slack_verified import slack_source
    from slack_verified.helpers import SlackApiException
except ImportError:  # pragma: no cover - optional template dependency
    dlt = None
    slack_source = None

    class SlackApiException(Exception):
        pass


log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"<@([A-Z0-9]+)(?:\|[^>]+)?>")
_SKIP_SUBTYPES = {"bot_message", "channel_join", "channel_leave"}


class SlackApiError(RuntimeError):
    """Raised when Slack rows cannot be fetched or normalized."""


def _require_dlt() -> None:
    if dlt is None or slack_source is None:
        raise SlackApiError(
            "dlt is not installed. Install the template extra with "
            '`uv pip install -e ".[personal-assistant]"`.'
        )


def _include_private_channels() -> bool:
    return os.environ.get("SLACK_INCLUDE_PRIVATE_CHANNELS", "").lower() in {"1", "true", "yes"}


def _include_bots() -> bool:
    return os.environ.get("SLACK_INCLUDE_BOTS", "").lower() in {"1", "true", "yes"}


def _parse_ts(value, fallback: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "in_timezone"):
        return value.in_timezone("UTC").naive().replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except ValueError:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
    return fallback or datetime.now(timezone.utc)


def fetch_verified_slack_rows(
    *,
    token: str,
    channels: Iterable[str],
    since: datetime,
    end_date: datetime | None = None,
    page_size: int = 200,
) -> tuple[list[dict], list[dict], list[dict], list[dict]]:
    """Fetch Slack rows with dlt's verified Slack source.

    The verified source handles Slack pagination and resource extraction. This
    function iterates its resources directly, then the adapter below groups rows
    into transcript-shaped thread documents for Cognee.
    """
    _require_dlt()
    try:
        source = slack_source(  # type: ignore[misc]
            page_size=page_size,
            access_token=token,
            start_date=since,
            end_date=end_date,
            selected_channels=list(channels),
            table_per_channel=False,
            replies=True,
            include_private_channels=_include_private_channels(),
        )
        return (
            list(source.channels),
            list(source.users),
            list(source.messages),
            list(source.replies),
        )
    except SlackApiException as exc:
        raise SlackApiError(str(exc)) from exc


def slack_thread_docs(
    *,
    token: str,
    channels: Iterable[str],
    since: datetime,
    personal_email: str | None = None,
    personal_slack_id: str | None = None,
    end_date: datetime | None = None,
) -> Iterator[Doc]:
    channels_rows, users_rows, messages_rows, replies_rows = fetch_verified_slack_rows(
        token=token,
        channels=channels,
        since=since,
        end_date=end_date,
    )
    yield from slack_rows_to_docs(
        channels_rows=channels_rows,
        users_rows=users_rows,
        messages_rows=messages_rows,
        replies_rows=replies_rows,
        personal_email=personal_email,
        personal_slack_id=personal_slack_id,
    )


def slack_rows_to_docs(
    *,
    channels_rows: Iterable[dict],
    users_rows: Iterable[dict],
    messages_rows: Iterable[dict],
    replies_rows: Iterable[dict],
    personal_email: str | None = None,
    personal_slack_id: str | None = None,
) -> Iterator[Doc]:
    channel_names = {
        row.get("id"): row.get("name") or row.get("id") for row in channels_rows if row.get("id")
    }
    user_labels = {_user_id(row): _user_label(row) for row in users_rows if _user_id(row)}

    threads: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for message in messages_rows:
        if _is_skippable_message(message):
            continue
        thread_ts = str(message.get("thread_ts") or message.get("ts"))
        threads[(message.get("channel"), thread_ts)].append(message)

    for reply in replies_rows:
        if _is_skippable_message(reply):
            continue
        thread_ts = str(reply.get("thread_ts") or reply.get("ts"))
        key = (reply.get("channel"), thread_ts)
        existing_ts = {str(message.get("ts")) for message in threads.get(key, [])}
        if str(reply.get("ts")) not in existing_ts:
            threads[key].append(reply)

    for (channel_id, thread_ts), messages in threads.items():
        ordered = sorted(messages, key=lambda item: _parse_ts(item.get("ts")))
        utterances = [
            Utterance(
                speaker=_message_speaker(message, user_labels),
                timestamp=_parse_ts(message.get("ts")),
                text=_resolve_mentions(message.get("text") or "", user_labels),
            )
            for message in ordered
            if (message.get("text") or "").strip()
        ]
        if not utterances:
            continue
        channel_name = channel_names.get(channel_id) or channel_id or "slack"
        title = f"#{channel_name}: {utterances[0].text.splitlines()[0][:80]}"
        extra_tags = [f"slack_channel_id:{channel_id}"]
        if _mentions_self(
            ordered,
            user_labels,
            personal_email=personal_email,
            personal_slack_id=personal_slack_id,
        ):
            extra_tags.append("mentioned_self:true")

        yield Doc(
            source="slack",
            doc_id=thread_ts,
            title=title,
            container=channel_name,
            started_at=utterances[0].timestamp,
            utterances=utterances,
            extra_tags=extra_tags,
        )


def _is_skippable_message(message: dict) -> bool:
    subtype = message.get("subtype")
    if subtype in _SKIP_SUBTYPES and not (subtype == "bot_message" and _include_bots()):
        return True
    return False


def _user_id(user: dict) -> str | None:
    return user.get("id") or user.get("user_id")


def _user_label(user: dict) -> str:
    profile = user.get("profile") or {}
    return (
        profile.get("email")
        or profile.get("real_name")
        or user.get("real_name")
        or user.get("name")
        or _user_id(user)
        or "unknown"
    )


def _message_speaker(message: dict, user_labels: dict[str, str]) -> str:
    user_id = message.get("user")
    if user_id:
        return user_labels.get(user_id, user_id)
    return message.get("username") or message.get("bot_id") or "unknown"


def _resolve_mentions(text: str, user_labels: dict[str, str]) -> str:
    return _MENTION_RE.sub(
        lambda match: f"@{user_labels.get(match.group(1), match.group(1))}",
        text,
    )


def _mentions_self(
    messages: Iterable[dict],
    user_labels: dict[str, str],
    *,
    personal_email: str | None,
    personal_slack_id: str | None,
) -> bool:
    if not (personal_email or personal_slack_id):
        return False
    email = personal_email.lower() if personal_email else None
    slack_id = personal_slack_id
    slack_label = user_labels.get(slack_id, "").lower() if slack_id else None
    for message in messages:
        text = message.get("text") or ""
        resolved = _resolve_mentions(text, user_labels).lower()
        if email and email in resolved:
            return True
        if slack_id and f"<@{slack_id}" in text:
            return True
        if slack_label and slack_label in resolved:
            return True
    return False
