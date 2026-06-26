"""GTM brain source: read the modelguide "brain" folder into the graph.

Unlike the live Slack/Granola sources, the GTM brain is a *folder of
files* (the dataset shipped in ``sample_data/gtm_brain/``). It mixes
three shapes, and each maps to the graph differently:

- **Structured tables** (``tables/*.csv``) and the **calendar**
  (``calendar_next-24h.ics``) → deterministic DataPoints
  (:class:`Company`, :class:`Person`, :class:`Deal`, :class:`Signal`,
  :class:`CalendarEvent`, :class:`Event`). No LLM. These are *seeded
  first* so they become the canonical nodes that conversations attach
  to.
- **ICP / account docs** (``icp_*.md``, ``account-deep-dive_*.md``) →
  deterministic :class:`ICP` nodes and Company enrichment.
- **Conversations** (``granola_*.md``, ``email-threads/*.md``) →
  :class:`Doc` objects that the ingest pipeline cognifies into the
  :class:`Thread` graph, exactly like the Slack/Granola path.

Everything fuses on ``Person.email`` and ``Company.domain``.
"""

from __future__ import annotations

import csv
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator

from ..gtm_people import Roster
from ..normalize import Doc, Utterance
from ..schema import CalendarEvent, Company, Deal, Event, ICP, Person, Signal

log = logging.getLogger(__name__)

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_SPEAKER_RE = re.compile(r"^\*\*(.+?):\*\*\s?(.*)$")
_EMAIL_IN_ANGLE_RE = re.compile(r"<([^>]+@[^>]+)>")
_FIELD_RE = re.compile(r"^\*\*(From|To|Cc|Date|Subject):\*\*\s*(.*)$", re.IGNORECASE)


# Static editions referenced across the dataset. Warsaw is the past
# edition the debrief reflects on; London is the one every deal targets.
EVENTS: list[Event] = [
    Event(name="Warsaw 2026", city="Warsaw", edition_date="2026", status="past"),
    Event(
        name="GTM Tech Week London 2027",
        city="London",
        edition_date="2027",
        status="planning",
    ),
]


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter dict, body). Tolerant of none."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    try:
        import yaml

        meta = yaml.safe_load(m.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception as exc:  # pragma: no cover - defensive
        log.warning("frontmatter parse failed: %s", exc)
        meta = {}
    return meta, m.group(2)


def _parse_ics_dt(value: str) -> str:
    """``20260626T100000Z`` → ISO ``2026-06-26T10:00:00+00:00``."""
    value = value.strip()
    try:
        if value.endswith("Z"):
            dt = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        else:
            dt = datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)
        return dt.isoformat()
    except ValueError:
        return value


def _to_float(value: str | None) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _to_int(value: str | None) -> int | None:
    try:
        return int(float(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


class GTMBrainSource:
    """Reads one GTM brain folder. Build order matters: companies and
    people are resolved first so deals/signals/calendar/threads link to
    canonical nodes."""

    def __init__(self, root: str | Path, roster: Roster | None = None) -> None:
        self.root = Path(root)
        self.roster = roster or Roster()
        self._companies: dict[str, Company] = {}
        self._events = {e.name: e for e in EVENTS}

    # -- helpers -----------------------------------------------------------

    def _tables(self) -> Path:
        return self.root / "tables"

    def _read_csv(self, name: str) -> list[dict]:
        path = self._tables() / name
        if not path.exists():
            log.info("gtm: %s not present, skipping", name)
            return []
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))

    def _company(self, domain: str | None, name: str | None = None) -> Company | None:
        if not domain:
            return None
        domain = domain.strip().lower()
        existing = self._companies.get(domain)
        if existing is not None:
            return existing
        company = Company(name=name or domain.split(".")[0].title(), domain=domain)
        self._companies[domain] = company
        return company

    def _event(self, name: str | None) -> Event | None:
        if not name:
            return None
        return self._events.get(name.strip())

    # -- structured entities ----------------------------------------------

    def companies(self) -> list[Company]:
        """Build canonical Company nodes from the company table, enriched
        by the lookalike scores, Clay prospect tiers, and do-not-approach
        flags."""
        scores = {
            r["domain"].strip().lower(): _to_int(r.get("icp_fit_score"))
            for r in self._read_csv("lookalike_features.csv")
            if r.get("domain")
        }
        prospects = {
            r["domain"].strip().lower(): r
            for r in self._read_csv("clay_table_sponsor-prospects.csv")
            if r.get("domain")
        }
        blocked = {
            r["domain"].strip().lower()
            for r in self._read_csv("do-not-approach.csv")
            if r.get("domain")
        }

        for row in self._read_csv("attio_companies.csv"):
            domain = (row.get("domain") or "").strip().lower()
            if not domain:
                continue
            company = self._company(domain, row.get("name"))
            assert company is not None  # domain validated above
            company.name = row.get("name") or company.name
            company.segment = row.get("segment") or None
            company.hq_city = row.get("hq_city") or None
            company.size_band = row.get("size_band") or None
            company.is_past_sponsor = _truthy(row.get("is_past_sponsor"))
            company.notes = row.get("notes") or None
            company.icp_fit_score = scores.get(domain)
            prospect = prospects.get(domain)
            if prospect:
                company.tier = prospect.get("tier") or company.tier
                if company.icp_fit_score is None:
                    company.icp_fit_score = _to_int(prospect.get("icp_fit_score"))
            company.do_not_approach = (
                domain in blocked or str(row.get("status")).strip().lower() == "do not approach"
            )
        # Account deep-dives enrich the matching company with rich notes.
        self._apply_account_deepdives()
        return list(self._companies.values())

    def people(self) -> list[Person]:
        """Register the speaker roster onto the shared Roster and return
        all canonical Person nodes discovered so far."""
        for row in self._read_csv("apollo_people-export_speakers.csv"):
            email = (row.get("email") or "").strip()
            if not email:
                continue
            self.roster.register(
                Person(
                    email=email,
                    name=row.get("name") or email.split("@")[0],
                    title=row.get("title") or None,
                    company_domain=(row.get("company_domain") or "").strip().lower() or None,
                    speaker_tier=row.get("tier") or None,
                    linkedin_url=row.get("person_linkedin_url") or None,
                )
            )
        return self.roster.all()

    def deals(self) -> list[Deal]:
        out: list[Deal] = []
        for row in self._read_csv("attio_deals.csv"):
            name = (row.get("deal_name") or "").strip()
            if not name:
                continue
            out.append(
                Deal(
                    name=name,
                    kind=(row.get("kind") or "sponsorship").strip(),
                    stage=(row.get("stage") or "Discovery").strip(),
                    company=self._company(row.get("company_domain"), row.get("company")),
                    event=self._event(row.get("event")),
                    amount=_to_float(row.get("amount")),
                    currency=(row.get("currency") or "").strip() or None,
                    owner_email=(row.get("owner_email") or "").strip() or None,
                    next_step=(row.get("next_step") or "").strip() or None,
                )
            )
        return out

    def signals(self) -> list[Signal]:
        out: list[Signal] = []
        for row in self._read_csv("signals_feed.csv"):
            desc = (row.get("description") or "").strip()
            if not desc:
                continue
            entity_type = (row.get("entity_type") or "").strip().lower()
            company = person = None
            if entity_type == "company":
                company = self._company(row.get("entity_domain"), row.get("entity"))
            elif entity_type == "person":
                # person signals key off the company domain in the feed
                person = self.roster.by_name(row.get("entity") or "")
            out.append(
                Signal(
                    description=desc,
                    signal_kind=(row.get("signal_kind") or "other").strip(),
                    observed_on=(row.get("observed_on") or "").strip(),
                    company=company,
                    person=person,
                    source=(row.get("source") or "").strip() or None,
                )
            )
        return out

    def events(self) -> list[Event]:
        return list(self._events.values())

    def calendar_events(self) -> list[CalendarEvent]:
        path = self.root / "calendar_next-24h.ics"
        if not path.exists():
            return []
        return list(self._parse_ics(path.read_text(encoding="utf-8")))

    def icps(self) -> list[ICP]:
        out: list[ICP] = []
        for path in sorted(self.root.glob("icp_*.md")):
            out.append(self._parse_icp(path))
        return out

    # -- conversations (cognified) ----------------------------------------

    def conversation_docs(self) -> Iterator[Doc]:
        for path in sorted(self.root.glob("granola_*.md")):
            doc = self._parse_granola(path)
            if doc.utterances:
                yield doc
        for path in sorted((self.root / "email-threads").glob("*.md")):
            doc = self._parse_email_thread(path)
            if doc.utterances:
                yield doc

    # -- parsers -----------------------------------------------------------

    def _apply_account_deepdives(self) -> None:
        for path in sorted(self.root.glob("account-deep-dive_*.md")):
            meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
            domain = (meta.get("domain") or "").strip().lower()
            if not domain:
                continue
            company = self._company(domain, meta.get("account"))
            assert company is not None  # domain validated above
            # Keep the prose retrievable on the Company node (notes is an
            # index field), capped so we don't embed an essay.
            notes = (body or "").strip()
            if notes:
                company.notes = notes[:4000]

    def _parse_icp(self, path: Path) -> ICP:
        _, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        name = path.stem.replace("icp_", "").strip() or "icp"
        one_liner = self._section(body, "The one-line ICP") or body.strip().splitlines()[:1][0]
        segments = self._bullets(self._section(body, "sub-segments") or self._section(body, "Three sub-segments") or "")
        signals = self._bullets(self._section(body, '"Why now" triggers') or self._section(body, "Why now") or "")
        return ICP(
            name=name,
            one_liner=" ".join(one_liner.split())[:400],
            description=body.strip()[:4000],
            segments=segments[:8],
            signals=signals[:8],
        )

    def _parse_granola(self, path: Path) -> Doc:
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        title = (meta.get("title") or path.stem).strip()
        account = (meta.get("account") or "").strip()
        domain = (meta.get("domain") or "").strip().lower()
        started = self._meta_date(meta)
        utterances = list(self._transcript_utterances(body, started))
        extra_tags = ["source:granola", "channel:granola"]
        if account:
            extra_tags.append(f"account:{account.lower()}")
        if domain:
            extra_tags.append(f"company:{domain}")
        if str(meta.get("transcript_status", "")).lower() == "partial":
            extra_tags.append("transcript:partial")
        return Doc(
            source="granola",
            doc_id=path.stem,
            title=title,
            container=account or "granola",
            started_at=started,
            utterances=utterances,
            extra_tags=extra_tags,
        )

    def _parse_email_thread(self, path: Path) -> Doc:
        meta, body = _parse_frontmatter(path.read_text(encoding="utf-8"))
        subject = (meta.get("subject") or path.stem).strip()
        account = (meta.get("account") or "").strip()
        domain = (meta.get("domain") or "").strip().lower()
        utterances = list(self._email_utterances(body))
        started = utterances[0].timestamp if utterances else self._meta_date(meta)
        extra_tags = ["source:email", "channel:email"]
        if account:
            extra_tags.append(f"account:{account.lower()}")
        if domain:
            extra_tags.append(f"company:{domain}")
        return Doc(
            source="email",
            doc_id=path.stem,
            title=subject,
            container=account or "email",
            started_at=started,
            utterances=utterances,
            extra_tags=extra_tags,
        )

    def _transcript_utterances(self, body: str, started: datetime) -> Iterator[Utterance]:
        """Parse the ``## Transcript`` section into speaker-attributed
        utterances. Wrapped lines are coalesced; ``[inaudible]`` /
        ``[recording dropped]`` markers are preserved verbatim."""
        section = self._section_raw(body, "Transcript")
        if not section:
            return
        speaker: str | None = None
        buf: list[str] = []
        idx = 0

        def flush() -> Iterator[Utterance]:
            nonlocal buf, idx
            if speaker and buf:
                text = " ".join(s.strip() for s in buf if s.strip()).strip()
                if text:
                    person = self.roster.by_name(speaker)
                    yield Utterance(
                        speaker=person.email,
                        timestamp=started + timedelta(minutes=idx),
                        text=text,
                    )
                    idx += 1
            buf = []

        for line in section.splitlines():
            if line.strip().startswith("*[") or line.strip() in {"---", ""}:
                if line.strip().startswith("*["):
                    yield from flush()
                    speaker = None
                continue
            m = _SPEAKER_RE.match(line.strip())
            if m:
                yield from flush()
                speaker = m.group(1).strip()
                buf = [m.group(2)]
            elif speaker is not None:
                buf.append(line)
        yield from flush()

    def _email_utterances(self, body: str) -> Iterator[Utterance]:
        """Each ``---``-delimited message block becomes one Utterance,
        attributed to the From: address."""
        blocks = re.split(r"\n---\s*\n", body)
        for block in blocks:
            fields: dict[str, str] = {}
            body_lines: list[str] = []
            in_body = False
            for line in block.splitlines():
                fm = _FIELD_RE.match(line.strip())
                if fm and not in_body:
                    fields[fm.group(1).lower()] = fm.group(2).strip()
                elif line.strip() == "" and fields and not in_body:
                    in_body = True
                elif in_body:
                    body_lines.append(line)
            sender = fields.get("from")
            if not sender:
                continue
            email_m = _EMAIL_IN_ANGLE_RE.search(sender)
            name = sender.split("<")[0].strip() or None
            email = email_m.group(1) if email_m else sender.strip()
            person = self.roster.by_email(email, name)
            ts = self._parse_email_date(fields.get("date"))
            subject = fields.get("subject", "")
            text = "\n".join(body_lines).strip()
            rendered = f"[Subject: {subject}] {text}".strip() if subject else text
            if rendered:
                yield Utterance(speaker=person.email, timestamp=ts, text=rendered)

    def _parse_ics(self, text: str) -> Iterator[CalendarEvent]:
        # Unfold folded lines (continuation lines start with a space/tab).
        unfolded: list[str] = []
        for raw in text.splitlines():
            if raw[:1] in (" ", "\t") and unfolded:
                unfolded[-1] += raw[1:]
            else:
                unfolded.append(raw)

        cur: dict | None = None
        attendees: list[Person] = []
        organizer: Person | None = None
        for line in unfolded:
            if line.strip() == "BEGIN:VEVENT":
                cur, attendees, organizer = {}, [], None
                continue
            if line.strip() == "END:VEVENT" and cur is not None:
                domains = {a.email.split("@")[-1].lower() for a in attendees}
                about = None
                for dom in domains:
                    about = self._company(dom) if dom in self._companies else about
                yield CalendarEvent(
                    uid=cur.get("uid", cur.get("summary", "event")),
                    summary=cur.get("summary", ""),
                    starts_at=cur.get("start", ""),
                    ends_at=cur.get("end"),
                    location=cur.get("location"),
                    description=cur.get("description"),
                    organizer=organizer,
                    attendees=attendees,
                    about_company=about,
                )
                cur = None
                continue
            if cur is None:
                continue
            key, _, val = line.partition(":")
            key_up = key.upper()
            if key_up == "UID":
                cur["uid"] = val.strip()
            elif key_up == "SUMMARY":
                cur["summary"] = val.strip()
            elif key_up == "DESCRIPTION":
                cur["description"] = val.strip()
            elif key_up == "LOCATION":
                cur["location"] = val.strip()
            elif key_up.startswith("DTSTART"):
                cur["start"] = _parse_ics_dt(val)
            elif key_up.startswith("DTEND"):
                cur["end"] = _parse_ics_dt(val)
            elif key_up.startswith("ORGANIZER"):
                organizer = self._person_from_ics(key, val)
            elif key_up.startswith("ATTENDEE"):
                p = self._person_from_ics(key, val)
                if p:
                    attendees.append(p)

    def _person_from_ics(self, key: str, val: str) -> Person | None:
        cn_m = re.search(r"CN=([^;:]+)", key)
        name = cn_m.group(1).strip() if cn_m else None
        email_m = re.search(r"mailto:([^\s>]+@[^\s>]+)", val, re.IGNORECASE)
        if not email_m:
            return None
        return self.roster.by_email(email_m.group(1).strip(), name)

    # -- small text utilities ---------------------------------------------

    def _meta_date(self, meta: dict) -> datetime:
        raw = str(meta.get("date") or "").strip()
        if raw:
            try:
                return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _parse_email_date(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        value = value.strip()
        for fmt in ("%Y-%m-%d, %H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return datetime.now(timezone.utc)

    @staticmethod
    def _section_raw(body: str, heading_contains: str) -> str | None:
        """Return the text under the first ``##`` heading containing the
        given phrase, up to the next heading of the same/greater level."""
        lines = body.splitlines()
        start = None
        for i, line in enumerate(lines):
            if line.lstrip().startswith("#") and heading_contains.lower() in line.lower():
                start = i + 1
                break
        if start is None:
            return None
        out: list[str] = []
        for line in lines[start:]:
            if line.lstrip().startswith("## ") or line.startswith("# "):
                break
            out.append(line)
        return "\n".join(out).strip() or None

    def _section(self, body: str, heading_contains: str) -> str | None:
        return self._section_raw(body, heading_contains)

    @staticmethod
    def _bullets(section: str) -> list[str]:
        out: list[str] = []
        for line in (section or "").splitlines():
            s = line.strip().lstrip("-*0123456789.").strip()
            s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)  # drop bold markers
            if s and len(s) > 3:
                out.append(s[:200])
        return out
