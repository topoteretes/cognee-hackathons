"""Ingestion entrypoint: pull from configured sources, write to Cognee.

v2 mode (default):
- Pre-seed canonical Person nodes from the Slack workspace.
- For every thread/meeting, run the two-axis LLM classifier and attach
  the resulting product/client/domain tags.
- Write via cognee.add + cognify(graph_model=Thread) so the graph gets
  typed Message/Person/Topic/Decision nodes.
- Process docs concurrently with INGEST_CONCURRENCY workers.

Set INGEST_V2=0 (or INGEST_LEGACY=1) to fall back to the v0 free-form
``remember`` path.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass

from pathlib import Path

from .classifier import Classifier
from .cognee_client import add_doc, cognify_threads, connect, seed_points, write, write_typed
from .gtm_people import Roster
from .normalize import Doc
from .people import seed_people
from .sources.granola import GranolaSource, since_from_env as granola_since
from .sources.gtm_files import GTMBrainSource
from .sources.slack import SlackSource, channels_from_env, since_from_env as slack_since

log = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestReport:
    slack_docs: int = 0
    granola_docs: int = 0
    failures: int = 0
    classified: int = 0
    seeded_people: int = 0
    # GTM brain
    gtm_companies: int = 0
    gtm_people: int = 0
    gtm_deals: int = 0
    gtm_signals: int = 0
    gtm_calendar: int = 0
    gtm_icps: int = 0
    gtm_threads: int = 0

    def total(self) -> int:
        return self.slack_docs + self.granola_docs + self.gtm_threads


def _v2_enabled() -> bool:
    if os.environ.get("INGEST_LEGACY", "").lower() in ("1", "true", "yes"):
        return False
    return os.environ.get("INGEST_V2", "1").lower() not in ("0", "false", "no")


def _concurrency() -> int:
    try:
        return max(1, int(os.environ.get("INGEST_CONCURRENCY", "1")))
    except ValueError:
        return 1


async def _classify_and_write(
    doc: Doc,
    kind: str,
    classifier: Classifier | None,
    report: IngestReport,
    sem: asyncio.Semaphore,
) -> None:
    async with sem:
        extra_tags: list[str] = []
        if classifier is not None:
            try:
                routing = await classifier.classify(doc.body())
                extra_tags = routing.tags()
                report.classified += 1
            except Exception as e:
                log.warning("classifier error on %s/%s: %s", kind, doc.doc_id, e)
                extra_tags = ["domain:misc"]

        try:
            if _v2_enabled():
                await write_typed(doc, extra_tags=extra_tags)
            else:
                await write(doc)
            if kind == "slack":
                report.slack_docs += 1
            else:
                report.granola_docs += 1
            log.info(
                "wrote %s doc %s (%d utterances) tags=%s",
                kind,
                doc.doc_id,
                len(doc.utterances),
                extra_tags,
            )
        except Exception as exc:
            report.failures += 1
            log.warning(
                "failed to write %s doc %s: %s: %s",
                kind,
                doc.doc_id,
                type(exc).__name__,
                exc or "<no message>",
            )


async def ingest_slack(report: IngestReport, classifier: Classifier | None) -> None:
    if os.environ.get("SLACK_DISABLED", "").lower() in ("1", "true", "yes"):
        log.info("slack: SLACK_DISABLED set, skipping")
        return
    channels = channels_from_env()
    if not channels:
        log.info("slack: no SLACK_CHANNELS configured, skipping")
        return

    source = SlackSource()
    since = slack_since()
    log.info("slack: ingesting %d channel(s) since %s", len(channels), since.isoformat())

    sem = asyncio.Semaphore(_concurrency())
    tasks: list[asyncio.Task] = []
    for channel in channels:
        async for doc in source.fetch_threads(channel, since):
            tasks.append(
                asyncio.create_task(_classify_and_write(doc, "slack", classifier, report, sem))
            )
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def ingest_granola(report: IngestReport, classifier: Classifier | None) -> None:
    from .sources.granola import GranolaAuthError

    if os.environ.get("GRANOLA_DISABLED", "").lower() in ("1", "true", "yes"):
        log.info("granola: GRANOLA_DISABLED set, skipping")
        return

    try:
        source = GranolaSource()
    except GranolaAuthError as exc:
        log.info("granola: skipping — %s", exc)
        return

    since = granola_since()
    log.info("granola: ingesting since %s", since.isoformat())

    sem = asyncio.Semaphore(_concurrency())
    tasks: list[asyncio.Task] = []
    async for doc in source.fetch_notes(since):
        tasks.append(
            asyncio.create_task(_classify_and_write(doc, "granola", classifier, report, sem))
        )
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def _gtm_brain_dir() -> Path:
    """Resolve the GTM brain folder. Defaults to the vendored sample set."""
    raw = os.environ.get("GTM_BRAIN_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    # src/gtm_brain/ingest.py → project root → sample_data/gtm_brain
    return Path(__file__).resolve().parent.parent.parent / "sample_data" / "gtm_brain"


async def ingest_gtm_brain(report: IngestReport) -> None:
    """Ingest the GTM "brain" folder into the unified graph.

    Two-phase, and the order is load-bearing:

    1. Seed the *structured* entities (companies, people, events, deals,
       signals, calendar, ICPs) as canonical DataPoints. These become the
       nodes everything else attaches to — keyed by Company.domain and
       Person.email.
    2. Cognify the *conversations* (Granola transcripts + email threads)
       against the Thread schema. Because the canonical nodes already
       exist, the extracted messages/threads link onto them instead of
       creating duplicate people/companies.
    """
    if os.environ.get("GTM_BRAIN_DISABLED", "").lower() in ("1", "true", "yes"):
        log.info("gtm: GTM_BRAIN_DISABLED set, skipping")
        return

    root = _gtm_brain_dir()
    if not root.exists():
        log.warning("gtm: brain dir %s not found — skipping", root)
        return

    log.info("gtm: ingesting brain from %s", root)
    source = GTMBrainSource(root, roster=Roster())

    # Phase 1 — structured canonical nodes. companies()/people() must run
    # before deals()/signals()/calendar() so cross-references resolve.
    companies = source.companies()
    people = source.people()
    events = source.events()
    deals = source.deals()
    signals = source.signals()
    calendar = source.calendar_events()
    icps = source.icps()

    if not _v2_enabled():
        log.info("gtm: v2 disabled — seeding skipped, conversations only")
    else:
        report.gtm_companies = await seed_points(companies, label="companies")
        report.gtm_people = await seed_points(people, label="people")
        await seed_points(events, label="events")
        report.gtm_deals = await seed_points(deals, label="deals")
        report.gtm_signals = await seed_points(signals, label="signals")
        report.gtm_calendar = await seed_points(calendar, label="calendar events")
        report.gtm_icps = await seed_points(icps, label="ICPs")

    # Phase 2 — stage every conversation, then cognify once.
    staged = 0
    for doc in source.conversation_docs():
        try:
            if _v2_enabled():
                await add_doc(doc)
            else:
                await write(doc)
            staged += 1
        except Exception as exc:
            report.failures += 1
            log.warning("gtm: failed to stage %s: %s: %s", doc.doc_id, type(exc).__name__, exc)

    if staged and _v2_enabled():
        try:
            await cognify_threads()
            report.gtm_threads = staged
        except Exception as exc:
            report.failures += 1
            log.warning("gtm: cognify failed: %s: %s", type(exc).__name__, exc)
    elif not _v2_enabled():
        report.gtm_threads = staged

    log.info(
        "gtm: done — companies=%d people=%d deals=%d signals=%d calendar=%d icps=%d threads=%d",
        report.gtm_companies,
        report.gtm_people,
        report.gtm_deals,
        report.gtm_signals,
        report.gtm_calendar,
        report.gtm_icps,
        report.gtm_threads,
    )


async def _seed_people(report: IngestReport) -> None:
    """Pre-seed canonical Person nodes from Slack workspace."""
    if not _v2_enabled():
        return
    if os.environ.get("SLACK_DISABLED", "").lower() in ("1", "true", "yes"):
        return
    try:
        people = await seed_people()
        report.seeded_people = len(people)
        log.info("people: seeded %d persons", len(people))
    except Exception as exc:
        log.warning("people: seed failed (%s) — continuing without pre-seeded persons", exc)


async def run() -> IngestReport:
    await connect()
    report = IngestReport()
    classifier = Classifier() if _v2_enabled() else None
    await _seed_people(report)
    await ingest_slack(report, classifier)
    await ingest_granola(report, classifier)
    await ingest_gtm_brain(report)
    return report


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )
    report = asyncio.run(run())
    log.info(
        "ingest done — slack=%d granola=%d gtm_threads=%d failures=%d "
        "classified=%d seeded_people=%d | gtm: companies=%d people=%d deals=%d "
        "signals=%d calendar=%d icps=%d",
        report.slack_docs,
        report.granola_docs,
        report.gtm_threads,
        report.failures,
        report.classified,
        report.seeded_people,
        report.gtm_companies,
        report.gtm_people,
        report.gtm_deals,
        report.gtm_signals,
        report.gtm_calendar,
        report.gtm_icps,
    )


if __name__ == "__main__":
    main()
