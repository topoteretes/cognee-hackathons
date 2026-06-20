"""Normalized document shape shared by every source.

A Doc is what we hand to Cognee. The body is a transcript with one
line per utterance, prefixed by speaker and timestamp; structural
metadata (channel, project, participants) rides as node_set tags so
it stays queryable without bloating the extraction prompt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


_ISSUE_TERMS = (
    "bug",
    "issue",
    "error",
    "fail",
    "broken",
    "regression",
    "doesn't work",
    "does not work",
    "keeps ",
)


@dataclass(slots=True)
class Utterance:
    speaker: str
    timestamp: datetime
    text: str

    def render(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%dT%H:%M")
        return f"[{self.speaker}, {ts}] {self.text.strip()}"


@dataclass(slots=True)
class Doc:
    source: str
    doc_id: str
    title: str
    container: str
    started_at: datetime
    utterances: list[Utterance] = field(default_factory=list)
    project: str | None = None
    extra_tags: list[str] = field(default_factory=list)

    @property
    def participants(self) -> list[str]:
        seen: dict[str, None] = {}
        for u in self.utterances:
            seen.setdefault(u.speaker, None)
        return list(seen.keys())

    def transcript(self) -> str:
        return "\n".join(u.render() for u in self.utterances)

    def issue_candidates(self) -> list[Utterance]:
        candidates: list[Utterance] = []
        for utterance in self.utterances:
            text = utterance.text.lower()
            if any(term in text for term in _ISSUE_TERMS):
                candidates.append(utterance)
        return candidates

    def body(self) -> str:
        header = f"# {self.title}"
        parts = [header, self.transcript()]
        issues = self.issue_candidates()
        if issues:
            parts.append("## Reported issue candidates")
            parts.extend(f"- {issue.render()}" for issue in issues)
        return "\n".join(parts)

    def tags(self) -> list[str]:
        tags = [
            f"source:{self.source}",
            f"{self.source}:{self.container}",
            f"doc:{self.doc_id}",
            *(f"speaker:{p}" for p in self.participants),
        ]
        if self.project:
            tags.append(f"project:{self.project}")
        tags.extend(self.extra_tags)
        return tags
