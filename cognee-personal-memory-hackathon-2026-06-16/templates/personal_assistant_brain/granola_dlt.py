"""dlt source and Cognee adapter for Granola notes.

The public Granola API exposes a paginated notes endpoint and a per-note
endpoint that can include transcripts. This module keeps that API detail behind
a small dlt source, then converts each note into the shared Doc shape.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Iterable, Iterator

import httpx

from company_brain.normalize import Doc, Utterance

try:
    import dlt
except ImportError:  # pragma: no cover - optional template dependency
    dlt = None

log = logging.getLogger(__name__)

GRANOLA_API_BASE_URL = "https://public-api.granola.ai/v1"


class GranolaApiError(RuntimeError):
    """Raised when the Granola API cannot be queried."""


def _require_dlt() -> None:
    if dlt is None:
        raise GranolaApiError(
            "dlt is not installed. Install the template extra with "
            '`uv pip install -e ".[personal-assistant]"`.'
        )


def _api_base_url() -> str:
    return os.environ.get("GRANOLA_API_BASE_URL", GRANOLA_API_BASE_URL).rstrip("/")


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": "cognee-personal-assistant-brain/0.1",
    }


def _parse_ts(value, fallback: datetime | None = None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return fallback or datetime.now(timezone.utc)


def _list_notes(
    *,
    api_key: str,
    created_after: datetime,
    base_url: str,
    timeout: float,
) -> Iterator[dict]:
    cursor: str | None = None
    with httpx.Client(base_url=base_url, headers=_headers(api_key), timeout=timeout) as client:
        while True:
            params = {"created_after": created_after.isoformat().replace("+00:00", "Z")}
            if cursor:
                params["cursor"] = cursor
            resp = client.get("/notes", params=params)
            _raise_for_status(resp)
            payload = resp.json()
            for note in payload.get("notes", []):
                if note.get("id"):
                    yield note
            if not payload.get("hasMore"):
                break
            cursor = payload.get("cursor")
            if not cursor:
                break


def _get_note(
    *,
    api_key: str,
    note_id: str,
    base_url: str,
    timeout: float,
) -> dict:
    with httpx.Client(base_url=base_url, headers=_headers(api_key), timeout=timeout) as client:
        resp = client.get(f"/notes/{note_id}", params={"include": "transcript"})
        _raise_for_status(resp)
        note = resp.json()
        note.setdefault("id", note_id)
        return note


def _raise_for_status(resp: httpx.Response) -> None:
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        raise GranolaApiError(
            f"Granola API request failed: {exc.response.status_code} {body}"
        ) from exc


def fetch_granola_notes(
    *,
    api_key: str,
    created_after: datetime,
    note_ids: Iterable[str] | None = None,
    base_url: str | None = None,
    timeout: float = 30.0,
) -> Iterator[dict]:
    """Yield Granola notes with transcripts included."""
    api_base = (base_url or _api_base_url()).rstrip("/")
    ids = [note_id for note_id in (note_ids or []) if note_id]
    if ids:
        for note_id in ids:
            yield _get_note(
                api_key=api_key,
                note_id=note_id,
                base_url=api_base,
                timeout=timeout,
            )
        return

    for note in _list_notes(
        api_key=api_key,
        created_after=created_after,
        base_url=api_base,
        timeout=timeout,
    ):
        note_id = note["id"]
        try:
            yield _get_note(
                api_key=api_key,
                note_id=note_id,
                base_url=api_base,
                timeout=timeout,
            )
        except GranolaApiError as exc:
            log.warning("granola: skipping note %s: %s", note_id, exc)


if dlt is not None:

    @dlt.resource(name="granola_notes", primary_key="id", write_disposition="merge")
    def granola_notes_resource(
        api_key: str,
        created_after: datetime,
        note_ids: list[str] | None = None,
        base_url: str | None = None,
    ) -> Iterator[dict]:
        yield from fetch_granola_notes(
            api_key=api_key,
            created_after=created_after,
            note_ids=note_ids,
            base_url=base_url,
        )

    @dlt.source(name="granola")
    def granola_source(
        api_key: str,
        created_after: datetime,
        note_ids: list[str] | None = None,
        base_url: str | None = None,
    ):
        return granola_notes_resource(
            api_key=api_key,
            created_after=created_after,
            note_ids=note_ids,
            base_url=base_url,
        )


def granola_note_docs(
    *,
    api_key: str,
    created_after: datetime,
    note_ids: Iterable[str] | None = None,
    base_url: str | None = None,
) -> Iterator[Doc]:
    """Run the dlt Granola source and yield normalized Cognee Docs."""
    _require_dlt()
    source = granola_source(  # type: ignore[name-defined]
        api_key=api_key,
        created_after=created_after,
        note_ids=list(note_ids or []),
        base_url=base_url,
    )
    for note in source.granola_notes:
        yield granola_note_to_doc(note)


def granola_note_to_doc(note: dict) -> Doc:
    note_id = str(note.get("id") or note.get("uuid") or "")
    started_at = _parse_ts(
        note.get("created_at")
        or note.get("createdAt")
        or note.get("start_time")
        or note.get("started_at")
        or note.get("updated_at")
    )
    title = (note.get("title") or f"Granola note {note_id}").strip()
    owner = _person_label(note.get("owner")) or "owner"
    attendees = _attendee_labels(note)

    utterances = _transcript_utterances(
        note.get("transcript") or [],
        fallback_ts=started_at,
        owner=owner,
    )
    if not utterances and note.get("summary"):
        utterances = [
            Utterance(speaker="granola_summary", timestamp=started_at, text=note["summary"])
        ]

    extra_tags = [f"owner:{owner}", *(f"attendee:{person}" for person in attendees)]
    if note.get("url"):
        extra_tags.append(f"url:{note['url']}")

    return Doc(
        source="granola",
        doc_id=note_id,
        title=title,
        container="granola",
        started_at=started_at,
        utterances=utterances,
        extra_tags=extra_tags,
    )


def _transcript_utterances(
    transcript: list[dict],
    *,
    fallback_ts: datetime,
    owner: str,
) -> list[Utterance]:
    utterances: list[Utterance] = []
    for item in transcript:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        speaker = _transcript_speaker(item.get("speaker"), owner)
        ts = _parse_ts(
            item.get("start_timestamp")
            or item.get("start_time")
            or item.get("timestamp")
            or item.get("created_at"),
            fallback=fallback_ts,
        )
        utterances.append(Utterance(speaker=speaker, timestamp=ts, text=text))
    return _merge_adjacent_utterances(utterances)


def _merge_adjacent_utterances(utterances: list[Utterance]) -> list[Utterance]:
    merged: list[Utterance] = []
    for utterance in utterances:
        if merged and merged[-1].speaker == utterance.speaker:
            merged[-1].text = f"{merged[-1].text} {utterance.text}"
        else:
            merged.append(utterance)
    return merged


def _transcript_speaker(raw_speaker, owner: str) -> str:
    if not isinstance(raw_speaker, dict):
        return "unknown"
    person = _person_label(raw_speaker)
    if person:
        return person
    label = raw_speaker.get("diarization_label")
    if label:
        return str(label)
    source = raw_speaker.get("source")
    if source == "microphone":
        return owner
    if source:
        return str(source)
    return "unknown"


def _person_label(person) -> str | None:
    if isinstance(person, str):
        return person.strip() or None
    if not isinstance(person, dict):
        return None
    email = person.get("email") or person.get("address")
    if email:
        return str(email)
    name = person.get("name") or person.get("display_name")
    return str(name).strip() if name else None


def _attendee_labels(note: dict) -> list[str]:
    people: list[str] = []
    for key in ("attendees", "participants", "people"):
        raw = note.get(key)
        if isinstance(raw, list):
            for person in raw:
                label = _person_label(person)
                if label:
                    people.append(label)
    return list(dict.fromkeys(people))
