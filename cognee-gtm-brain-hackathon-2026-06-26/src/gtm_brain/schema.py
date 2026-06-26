"""Typed DataPoints for the unified GTM-brain graph.

This schema merges two worlds into one graph:

1. **Conversation graph** (inherited from the company-brain pipeline) —
   Slack threads and Granola/email transcripts become a :class:`Thread`
   root carrying :class:`Message` nodes, each linked to a :class:`Person`
   speaker, with :class:`Topic`/:class:`Question`/:class:`Issue`/
   :class:`Decision` emerging from message bodies.

2. **GTM graph** (the modelguide "brain" extension) — the accounts,
   sponsors, speakers, deals, signals and calendar around running
   *GTM Tech Week* (Warsaw 2026 → London 2027). These are mostly
   *structured* inputs (CSV/ICS), so they are pre-seeded as canonical
   DataPoints *before* conversations are cognified.

The two worlds fuse on two identity anchors:

- :class:`Person` keyed by ``email`` — a speaker in a Granola transcript,
  a recipient on an email thread, and a calendar attendee all collapse
  onto one node.
- :class:`Company` keyed by ``domain`` — the account in
  ``attio_companies.csv``, the sponsor prospect in the Clay table, the
  ``company`` a thread is about, and the company mentioned in a meeting
  all collapse onto one node.

Because the structured Company/Person/Deal nodes are seeded first, when
the LLM cognifies "Clay — sponsorship intro" it attaches Bruno's
messages onto the existing ``bruno@clay.com`` Person and links the
Thread to the existing ``clay.com`` Company — so the call, the email
thread, the deal, the deep-dive and the calendar invite are all one
connected subgraph.
"""

from __future__ import annotations

from typing import Optional

from cognee.low_level import DataPoint


# --------------------------------------------------------------------------- #
# People & organisations — the shared identity anchors
# --------------------------------------------------------------------------- #


class Person(DataPoint):
    email: str
    name: str
    slack_id: Optional[str] = None
    # GTM-side facets (optional — only set for the speaker roster)
    title: Optional[str] = None
    company_domain: Optional[str] = None
    speaker_tier: Optional[str] = None  # A / B / C from the speaker ICP
    linkedin_url: Optional[str] = None
    metadata: dict = {"index_fields": ["email", "name"], "identity_fields": ["email"]}


class Company(DataPoint):
    """A canonical external organisation, keyed by ``domain``.

    Supersedes the old ``Client`` catch-all: an account in Attio, a
    sponsor prospect, the company a thread is *about*, and a speaker's
    employer all resolve to one Company node via ``domain``.
    """

    name: str
    domain: str
    segment: Optional[str] = None  # revtech / service / investor / community / competitor
    hq_city: Optional[str] = None
    size_band: Optional[str] = None
    icp_fit_score: Optional[int] = None  # 0–99 from lookalike_features.csv
    tier: Optional[str] = None  # A / B / C
    is_past_sponsor: bool = False
    do_not_approach: bool = False
    notes: Optional[str] = None
    metadata: dict = {
        "index_fields": ["name", "domain", "segment", "notes"],
        "identity_fields": ["domain"],
    }


# Backwards-compatible alias for the company-brain pipeline, which used a
# light ``Client`` node. New code should use Company.
class Client(Company):
    """Deprecated alias — an external company we work with. Use Company."""


class Product(DataPoint):
    """An internal product surface (cloud, sdk, mcp, …) or event track."""

    name: str
    metadata: dict = {"index_fields": ["name"]}


# --------------------------------------------------------------------------- #
# GTM structured entities — seeded from CSV/ICS before cognify
# --------------------------------------------------------------------------- #


class Event(DataPoint):
    """A GTM Tech Week edition (Warsaw 2026, London 2027, …)."""

    name: str
    city: Optional[str] = None
    edition_date: Optional[str] = None  # ISO date or free text
    status: Optional[str] = None  # past / planning / confirmed
    metadata: dict = {"index_fields": ["name", "city", "status"], "identity_fields": ["name"]}


class Deal(DataPoint):
    """A pipeline opportunity — sponsorship sale or speaker recruitment."""

    name: str
    kind: str  # sponsorship / speaking
    stage: str  # Discovery / Qualified / Proposal / Verbal Yes / Renewal …
    company: Optional[Company] = None
    event: Optional[Event] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    owner_email: Optional[str] = None
    next_step: Optional[str] = None
    metadata: dict = {
        "index_fields": ["name", "kind", "stage", "next_step"],
        "identity_fields": ["name"],
    }


class Signal(DataPoint):
    """A "why now" trigger watched on a Company or Person."""

    description: str
    signal_kind: str  # office_opened / raised_round / hiring_demand_gen / posting_ai_gtm …
    observed_on: str  # ISO date
    company: Optional[Company] = None
    person: Optional[Person] = None
    source: Optional[str] = None
    metadata: dict = {"index_fields": ["description", "signal_kind"]}


class CalendarEvent(DataPoint):
    """A scheduled meeting from the .ics feed (deterministic, no LLM)."""

    uid: str
    summary: str
    starts_at: str  # ISO timestamp
    ends_at: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    organizer: Optional[Person] = None
    attendees: list[Person] = []
    about_company: Optional[Company] = None
    metadata: dict = {"index_fields": ["summary", "description"], "identity_fields": ["uid"]}


class ICP(DataPoint):
    """An ideal-customer / ideal-speaker profile definition."""

    name: str  # "sponsor" or "speaker"
    one_liner: str
    description: str
    segments: list[str] = []
    signals: list[str] = []
    metadata: dict = {
        "index_fields": ["name", "one_liner", "description"],
        "identity_fields": ["name"],
    }


# --------------------------------------------------------------------------- #
# Conversation graph — Slack / Granola / email transcripts (cognified)
# --------------------------------------------------------------------------- #


class Topic(DataPoint):
    label: str
    aliases: list[str] = []
    metadata: dict = {"index_fields": ["label"]}


class Question(DataPoint):
    text: str
    asked_by: Person
    metadata: dict = {"index_fields": ["text"]}


class Decision(DataPoint):
    text: str
    decided_by: Optional[Person] = None
    metadata: dict = {"index_fields": ["text"]}


class Issue(DataPoint):
    """A concrete bug, problem, blocker, or risk raised in a thread."""

    summary: str
    reported_by: Person
    affected_area: Optional[str] = None
    observed_behavior: Optional[str] = None
    metadata: dict = {"index_fields": ["summary", "affected_area", "observed_behavior"]}


class Message(DataPoint):
    speaker: Person
    text: str
    sent_at: str  # ISO timestamp
    about: Optional[list[Topic]] = None
    raises: Optional[list[Question]] = None
    reports: Optional[list[Issue]] = None
    decides: Optional[list[Decision]] = None
    metadata: dict = {"index_fields": ["text"]}


class Thread(DataPoint):
    """The root for one Slack thread, Granola meeting, or email thread."""

    title: str
    source: str  # slack / granola / email
    doc_id: str
    channel: str
    started_at: str  # ISO timestamp
    participants: list[Person]
    messages: list[Message]
    product: Optional[Product] = None
    company: Optional[Company] = None  # the account this conversation is about
    event: Optional[Event] = None  # the GTM edition it relates to
    metadata: dict = {
        "index_fields": ["title", "source", "doc_id", "channel", "started_at"],
    }
