"""Personal Assistant Brain template runner.

This script is intentionally small: it defines the command shape and the
normalization boundary for a future dlt-backed implementation.

Usage:
    python templates/personal_assistant_brain/personal_assistant_brain.py ingest
    python templates/personal_assistant_brain/personal_assistant_brain.py ask "What do I owe today?"
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - template dependency is optional
    load_dotenv = None

from company_brain.cognee_client import connect, recall, visualize_graph, write_typed
from company_brain.normalize import Doc

from granola_dlt import GranolaApiError, granola_note_docs
from slack_dlt import SlackApiError, slack_thread_docs

log = logging.getLogger("personal_assistant_brain")


@dataclass(slots=True)
class PersonalIdentity:
    email: str | None = None
    slack_id: str | None = None
    name: str | None = None
    inferred_from: list[str] | None = None

    def is_uncertain(self) -> bool:
        return not (self.email or self.slack_id)


@dataclass(slots=True)
class TemplateReport:
    slack_docs: int = 0
    email_docs: int = 0
    granola_docs: int = 0
    skipped: list[str] | None = None

    def total(self) -> int:
        return self.slack_docs + self.email_docs + self.granola_docs

    def skip(self, source: str, reason: str) -> None:
        if self.skipped is None:
            self.skipped = []
        self.skipped.append(f"{source}: {reason}")


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv()
    os.environ.setdefault("COGNEE_DATASET", "personal_assistant_brain")


def _since_from_env() -> datetime:
    days = int(os.environ.get("INGEST_SINCE_DAYS", "30"))
    return datetime.now(timezone.utc) - timedelta(days=days)


def _resolve_identity(*, interactive: bool = True) -> PersonalIdentity:
    """Infer the user this personal assistant is for.

    Explicit PERSONAL_ASSISTANT_* values win. If absent, use source credentials
    that usually identify the owner. In an interactive shell, ask for feedback
    only when neither email nor Slack ID can be inferred.
    """
    sources: list[str] = []
    email = os.environ.get("PERSONAL_ASSISTANT_EMAIL") or os.environ.get("EMAIL_IMAP_USER")
    if os.environ.get("PERSONAL_ASSISTANT_EMAIL"):
        sources.append("PERSONAL_ASSISTANT_EMAIL")
    elif os.environ.get("EMAIL_IMAP_USER"):
        sources.append("EMAIL_IMAP_USER")

    slack_id = os.environ.get("PERSONAL_ASSISTANT_SLACK_ID") or os.environ.get("SLACK_USER_ID")
    if os.environ.get("PERSONAL_ASSISTANT_SLACK_ID"):
        sources.append("PERSONAL_ASSISTANT_SLACK_ID")
    elif os.environ.get("SLACK_USER_ID"):
        sources.append("SLACK_USER_ID")

    name = os.environ.get("PERSONAL_ASSISTANT_NAME")
    if name:
        sources.append("PERSONAL_ASSISTANT_NAME")

    identity = PersonalIdentity(
        email=email,
        slack_id=slack_id,
        name=name,
        inferred_from=sources,
    )
    if not identity.is_uncertain() or not interactive or not sys.stdin.isatty():
        return identity

    feedback = input(
        "Could not infer your identity. Enter your email or Slack user ID "
        "(leave blank to continue): "
    ).strip()
    if not feedback:
        return identity
    if "@" in feedback:
        identity.email = feedback
        os.environ["PERSONAL_ASSISTANT_EMAIL"] = feedback
    else:
        identity.slack_id = feedback
        os.environ["PERSONAL_ASSISTANT_SLACK_ID"] = feedback
    identity.inferred_from = ["user_feedback"]
    return identity


def _slack_dataset_name(doc: Doc) -> str:
    return f"slack:{doc.container}"


def _datasets_from_env() -> list[str] | None:
    raw = os.environ.get("COGNEE_DATASETS", "").strip()
    if not raw:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


async def _write_docs(
    docs: Iterable[Doc],
    *,
    dataset_name_for_doc: Callable[[Doc], str] | None = None,
) -> int:
    count = 0
    for doc in docs:
        dataset_name = dataset_name_for_doc(doc) if dataset_name_for_doc else None
        await write_typed(doc, dataset_name=dataset_name)
        count += 1
    return count


async def ingest_slack(report: TemplateReport) -> None:
    """Ingest Slack threads through the custom dlt source."""
    if os.environ.get("SLACK_DISABLED", "").lower() in {"1", "true", "yes"}:
        report.skip("slack", "SLACK_DISABLED set")
        return
    token = os.environ.get("SLACK_USER_TOKEN") or os.environ.get("SLACK_BOT_TOKEN")
    channels = [part.strip() for part in os.environ.get("SLACK_CHANNELS", "").split(",") if part.strip()]
    if not token:
        report.skip("slack", "missing SLACK_USER_TOKEN or SLACK_BOT_TOKEN")
        return
    if not channels:
        report.skip("slack", "missing SLACK_CHANNELS")
        return
    identity = _resolve_identity(interactive=False)
    try:
        docs = slack_thread_docs(
            token=token,
            channels=channels,
            since=_since_from_env(),
            personal_email=identity.email,
            personal_slack_id=identity.slack_id,
        )
        report.slack_docs = await _write_docs(docs, dataset_name_for_doc=_slack_dataset_name)
    except SlackApiError as exc:
        report.skip("slack", str(exc))


async def ingest_email(report: TemplateReport) -> None:
    """Future dlt-backed email ingestion.

    Planned implementation:
    - run dlt's verified Inbox source using EMAIL_IMAP_* env vars
    - group messages by Message-ID/In-Reply-To/References or normalized subject
    - normalize message bodies and attachment text into Docs
    """
    if os.environ.get("EMAIL_DISABLED", "").lower() in {"1", "true", "yes"}:
        report.skip("email", "EMAIL_DISABLED set")
        return
    required = ("EMAIL_IMAP_HOST", "EMAIL_IMAP_USER", "EMAIL_IMAP_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        report.skip("email", f"missing {', '.join(missing)}")
        return
    report.skip("email", "dlt adapter TODO")


async def ingest_granola(report: TemplateReport) -> None:
    """Ingest Granola notes through the custom dlt source."""
    if os.environ.get("GRANOLA_DISABLED", "").lower() in {"1", "true", "yes"}:
        report.skip("granola", "GRANOLA_DISABLED set")
        return
    api_key = os.environ.get("GRANOLA_API_KEY")
    if not api_key:
        report.skip("granola", "missing GRANOLA_API_KEY")
        return
    try:
        docs = granola_note_docs(
            api_key=api_key,
            created_after=_since_from_env(),
            note_ids=os.environ.get("GRANOLA_DOC_IDS", "").split(","),
            base_url=os.environ.get("GRANOLA_API_BASE_URL"),
        )
        report.granola_docs = await _write_docs(docs)
    except GranolaApiError as exc:
        report.skip("granola", str(exc))


async def ingest() -> TemplateReport:
    _load_env()
    _since_from_env()
    identity = _resolve_identity()
    if identity.is_uncertain():
        log.info("identity: uncertain; source-specific heuristics will be used")
    else:
        log.info("identity: inferred from %s", ", ".join(identity.inferred_from or []))
    await connect()
    report = TemplateReport()
    await ingest_slack(report)
    await ingest_email(report)
    await ingest_granola(report)
    return report


def _format_recall_row(row: object) -> str:
    text = getattr(row, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    raw = getattr(row, "raw", None)
    if isinstance(raw, dict):
        value = raw.get("value")
        if isinstance(value, str) and value.strip():
            return value

    if isinstance(row, dict):
        for key in ("text", "value"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raw = row.get("raw")
        if isinstance(raw, dict):
            value = raw.get("value")
            if isinstance(value, str) and value.strip():
                return value

    return str(row)


async def ask(question: str, datasets: list[str] | None = None) -> None:
    _load_env()
    await connect()
    rows = await recall(question, datasets=datasets or _datasets_from_env(), top_k=8)
    for row in rows:
        print(_format_recall_row(row))


async def visualize(output: str, dataset: str | None = None) -> Path:
    _load_env()
    await connect()
    out = Path(output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    await visualize_graph(str(out), dataset=dataset)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal Assistant Brain template")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="ingest configured personal-memory sources")
    ask_parser = sub.add_parser("ask", help="ask Cognee about personal memory")
    ask_parser.add_argument("question")
    ask_parser.add_argument(
        "--dataset",
        action="append",
        dest="datasets",
        help="Cognee dataset to query. Repeat for multiple datasets.",
    )
    visualize_parser = sub.add_parser("visualize", help="write Cognee's graph visualization to HTML")
    visualize_parser.add_argument(
        "--output",
        default="personal_assistant_brain_graph.html",
        help="HTML file to write.",
    )
    visualize_parser.add_argument(
        "--dataset",
        help="Optional Cognee dataset to visualize, e.g. personal_assistant_brain or slack:general.",
    )

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s - %(message)s")

    if args.command == "ingest":
        report = asyncio.run(ingest())
        log.info("ingest complete: total=%d", report.total())
        for skipped in report.skipped or []:
            log.info("skipped %s", skipped)
    elif args.command == "ask":
        asyncio.run(ask(args.question, datasets=args.datasets))
    elif args.command == "visualize":
        out = asyncio.run(visualize(args.output, dataset=args.dataset))
        log.info("graph visualization saved to %s", out)


if __name__ == "__main__":
    main()
