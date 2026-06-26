"""CLI entrypoints exposed via [project.scripts]."""

from __future__ import annotations

import asyncio
import logging
import os

from .env import load_project_env
from .ingest import main as ingest_main


def main() -> None:
    """Full ingest: Slack + Granola + the GTM brain folder."""
    load_project_env()
    ingest_main()


def brain_main() -> None:
    """GTM-brain-only ingest — no live Slack/Granola required.

    Reads ``sample_data/gtm_brain/`` (or ``$GTM_BRAIN_DIR``), seeds the
    structured GTM entities, and cognifies the conversations. Still needs
    ``LLM_API_KEY`` for cognify.
    """
    load_project_env()
    os.environ.setdefault("SLACK_DISABLED", "1")
    os.environ.setdefault("GRANOLA_DISABLED", "1")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    from .cognee_client import connect
    from .ingest import IngestReport, ingest_gtm_brain

    async def _run() -> IngestReport:
        await connect()
        report = IngestReport()
        await ingest_gtm_brain(report)
        return report

    report = asyncio.run(_run())
    logging.getLogger(__name__).info(
        "gtm ingest done — companies=%d people=%d deals=%d signals=%d "
        "calendar=%d icps=%d threads=%d failures=%d",
        report.gtm_companies,
        report.gtm_people,
        report.gtm_deals,
        report.gtm_signals,
        report.gtm_calendar,
        report.gtm_icps,
        report.gtm_threads,
        report.failures,
    )


if __name__ == "__main__":
    main()
