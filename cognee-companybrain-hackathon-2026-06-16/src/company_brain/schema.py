"""Typed DataPoints for the v2 graph.

Replaces Cognee's default ``Entity`` catch-all with a real schema. Each
ingested thread emits one :class:`Thread` root carrying a list of
:class:`Message` instances, each linked to a :class:`Person` speaker.
Topics and Decisions emerge from message bodies during cognify and get
attached as references.

Persons are pre-seeded from the Slack workspace user list (see
``people.py``) so mentions resolved to ``email`` form land on existing
nodes rather than creating duplicates.
"""

from __future__ import annotations

from typing import Optional

from cognee.low_level import DataPoint


class Person(DataPoint):
    email: str
    name: str
    slack_id: Optional[str] = None
    metadata: dict = {"index_fields": ["email", "name"], "identity_fields": ["email"]}


class Topic(DataPoint):
    label: str
    aliases: list[str] = []
    metadata: dict = {"index_fields": ["label"]}


class Client(DataPoint):
    """An external company we work with (a customer or partner)."""

    name: str
    metadata: dict = {"index_fields": ["name"]}


class Product(DataPoint):
    """An internal product surface (cloud, sdk, mcp, …)."""

    name: str
    metadata: dict = {"index_fields": ["name"]}


class Question(DataPoint):
    text: str
    asked_by: Person
    metadata: dict = {"index_fields": ["text"]}


class Decision(DataPoint):
    text: str
    decided_by: Optional[Person] = None
    metadata: dict = {"index_fields": ["text"]}


class Issue(DataPoint):
    """A concrete bug, problem, or unexpected behavior reported in a thread."""

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
    """The root for one Slack thread or Granola meeting."""

    channel: str
    started_at: str  # ISO timestamp
    participants: list[Person]
    messages: list[Message]
    product: Optional[Product] = None
    client: Optional[Client] = None
    metadata: dict = {"index_fields": ["channel"]}
