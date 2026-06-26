"""Granola source: pull meeting transcripts into Doc form.

Granola uses WorkOS for auth and its private API at api.granola.ai. The
desktop app caches an access token + refresh token in
``~/Library/Application Support/Granola/supabase.json`` (despite the
filename, contents are a WorkOS session). This source reads that file,
refreshes the access token when expired, then walks the documents and
their transcripts.

Endpoints (discovered, not officially published):
  POST /v2/get-documents                 — paginated list (metadata)
  POST /v1/get-document-transcript       — per-doc transcript segments

Each Granola meeting becomes one Doc; consecutive transcript segments
from the same source (microphone vs system audio) are merged into
single Utterances to keep the graph readable.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import AsyncIterator, Iterable

from ..normalize import Doc, Utterance

log = logging.getLogger(__name__)

_API_HOST = "api.granola.ai"
_AUTH_HOST = "auth.granola.ai"
_DEFAULT_CLIENT_VERSION = "7.277.1"
_DEFAULT_SESSION_FILE = (
    Path.home() / "Library" / "Application Support" / "Granola" / "supabase.json"
)
_FALLBACK_TOKEN_FILE = Path.home() / ".granola_access_token"
_SHARE_URL_RE = re.compile(r"notes\.granola\.ai/t/([^/?#]+)")
_DOC_URL_RE = re.compile(r"notes\.granola\.ai/d/([0-9a-fA-F-]{36})")


class GranolaAuthError(RuntimeError):
    """Raised when we can't obtain a valid access token."""


class GranolaAuth:
    """Reads the Granola desktop session, refreshing the access token on demand.

    The session file is written by the Granola Mac app. Opening Granola
    once before running ingest is the cheapest way to keep the refresh
    token alive; it rotates on every refresh roundtrip and we write the
    rotated token back to the file so the desktop app stays signed in.
    """

    def __init__(
        self,
        session_path: Path | None = None,
        client_version: str | None = None,
    ) -> None:
        self.session_path = session_path or _DEFAULT_SESSION_FILE
        self.client_version = client_version or os.environ.get(
            "GRANOLA_CLIENT_VERSION", _DEFAULT_CLIENT_VERSION
        )
        self._access_token: str | None = None
        self._access_expires_at: float = 0.0
        self._refresh_token: str | None = None
        self._client_id: str | None = None
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self.session_path.exists():
            raise GranolaAuthError(
                f"Granola session file not found at {self.session_path}. "
                "Open the Granola desktop app once to create it."
            )
        raw = json.loads(self.session_path.read_text(encoding="utf-8"))
        tokens = json.loads(raw["workos_tokens"])
        self._access_token = tokens.get("access_token")
        self._refresh_token = tokens.get("refresh_token")
        # client_id lives in the access_token's `iss` URL: .../client_<id>
        iss = self._decode_jwt_claim(self._access_token, "iss") if self._access_token else None
        if iss:
            self._client_id = iss.rstrip("/").rsplit("/", 1)[-1]
        # cache the expiry so we don't pay a refresh per call
        exp = self._decode_jwt_claim(self._access_token, "exp") if self._access_token else None
        self._access_expires_at = float(exp) if exp else 0.0

    @staticmethod
    def _decode_jwt_claim(jwt: str, claim: str):
        import base64

        try:
            payload = jwt.split(".")[1]
            payload += "=" * (-len(payload) % 4)
            body = json.loads(base64.urlsafe_b64decode(payload))
            return body.get(claim)
        except Exception:
            return None

    def access_token(self) -> str:
        """Return a fresh JWT, refreshing if the cached one is near expiry."""
        if self._access_token and self._access_expires_at - time.time() > 30:
            return self._access_token
        try:
            self._refresh()
        except GranolaAuthError as exc:
            # If refresh fails (e.g. refresh token already exchanged because
            # the desktop app refreshed in parallel), fall back to a manually
            # cached access token if one is present and still valid.
            fallback = self._load_fallback_token()
            if fallback:
                return fallback
            raise
        return self._access_token  # type: ignore[return-value]

    def _load_fallback_token(self) -> str | None:
        if not _FALLBACK_TOKEN_FILE.exists():
            return None
        jwt = _FALLBACK_TOKEN_FILE.read_text(encoding="utf-8").strip()
        exp = self._decode_jwt_claim(jwt, "exp") if jwt else None
        if exp and float(exp) - time.time() > 30:
            self._access_token = jwt
            self._access_expires_at = float(exp)
            log.info("granola: using fallback access token from %s", _FALLBACK_TOKEN_FILE)
            return jwt
        return None

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token()}",
            "X-Client-Version": self.client_version,
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip",
            "User-Agent": f"Granola/{self.client_version}",
        }

    def _refresh(self) -> None:
        if not (self._refresh_token and self._client_id):
            raise GranolaAuthError("missing refresh_token or client_id; cannot refresh")
        body = json.dumps(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            }
        ).encode()
        req = urllib.request.Request(
            f"https://{_AUTH_HOST}/user_management/authenticate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise GranolaAuthError(f"refresh failed: {e.code} {e.read().decode()[:200]}")

        self._access_token = payload["access_token"]
        self._refresh_token = payload.get("refresh_token") or self._refresh_token
        exp = self._decode_jwt_claim(self._access_token, "exp")
        self._access_expires_at = float(exp) if exp else (time.time() + 3000)
        log.info("granola: refreshed access token (expires in %ds)", int(self._access_expires_at - time.time()))
        self._persist_back()

    def _persist_back(self) -> None:
        """Rotate the new refresh token back into the desktop session file."""
        try:
            raw = json.loads(self.session_path.read_text(encoding="utf-8"))
            tokens = json.loads(raw["workos_tokens"])
            tokens["access_token"] = self._access_token
            tokens["refresh_token"] = self._refresh_token
            tokens["obtained_at"] = datetime.now(timezone.utc).isoformat()
            raw["workos_tokens"] = json.dumps(tokens)
            self.session_path.write_text(json.dumps(raw), encoding="utf-8")
        except Exception as e:
            log.warning("granola: could not write refreshed tokens back to %s: %s", self.session_path, e)


class GranolaSource:
    def __init__(self, auth: GranolaAuth | None = None) -> None:
        self.auth = auth or GranolaAuth()

    def _post(self, path: str, body: dict) -> tuple[int, dict | list]:
        req = urllib.request.Request(
            f"https://{_API_HOST}{path}",
            data=json.dumps(body).encode(),
            headers=self.auth.headers(),
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return resp.status, json.loads(raw) if raw else {}

    async def fetch_notes(self, since: datetime) -> AsyncIterator[Doc]:
        """Yield one Doc per meeting that started since `since`.

        If GRANOLA_DOC_IDS is set in the environment, ignores the date
        window entirely and emits only docs whose IDs match. Shared
        Granola URLs are resolved to their transcript document IDs.
        """
        allowlist = _doc_ids_from_env()
        if allowlist:
            log.info("granola: allowlist active (%d ids); ignoring date window", len(allowlist))

        direct_doc_ids = {doc_id for doc_id in allowlist if doc_id.startswith("direct:")}
        for direct_id in sorted(direct_doc_ids):
            doc_id = direct_id.removeprefix("direct:")
            doc = self._build_doc_by_id(doc_id)
            if doc.utterances:
                yield doc
        allowlist -= direct_doc_ids
        if direct_doc_ids and not allowlist:
            return

        cursor: str | None = None
        seen = 0
        while True:
            body: dict = {"limit": 200}
            if cursor:
                body["offset"] = cursor
            _, payload = self._post("/v2/get-documents", body)
            assert isinstance(payload, dict)
            docs = payload.get("docs", [])
            if not docs:
                break

            for d in docs:
                if allowlist:
                    if d.get("id") not in allowlist:
                        continue
                else:
                    created = _parse_ts(d.get("created_at"))
                    if created < since:
                        return  # docs come newest-first; stop scanning
                doc = self._build_doc(d)
                if doc.utterances:
                    seen += 1
                    yield doc
                    if allowlist and seen >= len(allowlist):
                        return

            cursor = payload.get("next_cursor")
            if not cursor:
                break
        log.info("granola: emitted %d docs", seen)

    def _build_doc(self, meta: dict) -> Doc:
        doc_id = meta["id"]
        title = (meta.get("title") or "Untitled meeting").strip()
        started_at = _parse_ts(meta.get("created_at"))
        creator_email, attendees = _extract_people(meta.get("people"))

        _, segs = self._post("/v1/get-document-transcript", {"document_id": doc_id})
        if not isinstance(segs, list):
            segs = []

        utterances = list(_segments_to_utterances(segs, creator_email))
        return Doc(
            source="granola",
            doc_id=doc_id,
            title=title,
            container=_container_for(attendees),
            started_at=started_at,
            utterances=utterances,
            extra_tags=[f"attendee:{a}" for a in attendees if a],
        )

    def _build_doc_by_id(self, doc_id: str) -> Doc:
        _, segs = self._post("/v1/get-document-transcript", {"document_id": doc_id})
        if not isinstance(segs, list):
            segs = []
        utterances = list(_segments_to_utterances(segs, None))
        started_at = utterances[0].timestamp if utterances else datetime.now(timezone.utc)
        return Doc(
            source="granola",
            doc_id=doc_id,
            title=f"Granola note {doc_id}",
            container="granola",
            started_at=started_at,
            utterances=utterances,
        )


def _segments_to_utterances(
    segments: Iterable[dict], creator_email: str | None
) -> Iterable[Utterance]:
    """Merge consecutive segments from the same source into one utterance.

    Granola STT emits 2–4 word chunks; storing them 1:1 would flood the
    graph with micro-nodes. We coalesce by `source` (microphone/system)
    and `detected_speaker_name` until either changes, then flush.
    """
    buf_text: list[str] = []
    buf_speaker: str | None = None
    buf_ts: datetime | None = None
    last_key: tuple | None = None

    def speaker_for(seg: dict) -> str:
        name = (seg.get("detected_speaker_name") or "").strip()
        if name:
            return name
        if seg.get("source") == "microphone" and creator_email:
            return creator_email
        return "guest" if seg.get("source") == "system" else (creator_email or "unknown")

    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text or not seg.get("is_final", True):
            continue
        key = (seg.get("source"), (seg.get("detected_speaker_name") or "").strip() or None)
        if key != last_key and buf_text:
            yield Utterance(
                speaker=buf_speaker or "unknown",
                timestamp=buf_ts or datetime.now(timezone.utc),
                text=" ".join(buf_text),
            )
            buf_text, buf_speaker, buf_ts = [], None, None
        if not buf_text:
            buf_speaker = speaker_for(seg)
            buf_ts = _parse_ts(seg.get("start_timestamp"))
        buf_text.append(text)
        last_key = key

    if buf_text:
        yield Utterance(
            speaker=buf_speaker or "unknown",
            timestamp=buf_ts or datetime.now(timezone.utc),
            text=" ".join(buf_text),
        )


def _extract_people(people: dict | list | None) -> tuple[str | None, list[str]]:
    """Return (creator_email, attendee_emails)."""
    if not people:
        return None, []
    if isinstance(people, list):
        attendees = [_email_of(p) for p in people]
        return None, [a for a in attendees if a]
    creator = people.get("creator")
    creator_email = _email_of(creator) if creator else None
    raw_attendees = people.get("attendees") or []
    attendees = [_email_of(a) for a in raw_attendees]
    return creator_email, [a for a in attendees if a]


def _email_of(p: dict | str | None) -> str | None:
    if not p:
        return None
    if isinstance(p, str):
        return p if "@" in p else None
    return p.get("email") or p.get("address") or None


def _container_for(attendees: list[str]) -> str:
    """Coarse grouping. With no calendar info, all meetings share one container."""
    return "granola"


def _parse_ts(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def since_from_env() -> datetime:
    days = int(os.environ.get("INGEST_SINCE_DAYS", "30"))
    return datetime.now(timezone.utc) - timedelta(days=days)


def _doc_ids_from_env() -> set[str]:
    raw = os.environ.get("GRANOLA_DOC_IDS", "").strip()
    if not raw:
        return set()
    return {_resolve_doc_id(p.strip()) for p in raw.split(",") if p.strip()}


def _resolve_doc_id(value: str) -> str:
    doc_url = _DOC_URL_RE.search(value)
    if doc_url:
        return f"direct:{doc_url.group(1)}"
    share_url = _SHARE_URL_RE.search(value)
    if share_url:
        return f"direct:{_resolve_share_token(share_url.group(1))}"
    return value


def _resolve_share_token(token: str) -> str:
    req = urllib.request.Request(
        f"https://notes.granola.ai/t/{token}",
        headers={"User-Agent": "Mozilla/5.0"},
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(req, timeout=10)
    except urllib.error.HTTPError as exc:
        if exc.code not in {301, 302, 303, 307, 308}:
            raise
        location = exc.headers.get("Location", "")
        doc_url = _DOC_URL_RE.search(location)
        if doc_url:
            return doc_url.group(1)
    raise GranolaAuthError(f"could not resolve Granola share token {token!r}")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
