from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class HtmlDocument:
    """Normalized representation of one uploaded HTML document."""

    doc_id: str
    filename: str
    title: str
    url: str | None
    text: str
    sections: list[dict[str, str]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class QueryEvidence:
    source: str
    title: str
    snippet: str
    score: float


@dataclass(slots=True)
class AnswerResult:
    answer: str
    evidence: list[QueryEvidence]
    metrics: dict[str, float | int | str]
