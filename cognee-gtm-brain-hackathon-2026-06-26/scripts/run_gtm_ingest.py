#!/usr/bin/env python3
"""Ingest ONLY the GTM brain folder — no live Slack/Granola needed.

This is the offline path used by the tutorial and the hackathon
quickstart: it reads ``sample_data/gtm_brain/`` (or ``$GTM_BRAIN_DIR``),
seeds the structured GTM entities, and cognifies the conversations into
the unified graph. Requires ``LLM_API_KEY`` in ``.env`` (cognify uses an
LLM); no Slack/Granola tokens required.

    python scripts/run_gtm_ingest.py
"""

from __future__ import annotations

import asyncio
import logging
import os

from gtm_brain.env import load_project_env


def main() -> None:
    load_project_env()
    # Make this a pure GTM-brain run regardless of what else is configured.
    os.environ.setdefault("SLACK_DISABLED", "1")
    os.environ.setdefault("GRANOLA_DISABLED", "1")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    from gtm_brain.cognee_client import connect
    from gtm_brain.ingest import IngestReport, ingest_gtm_brain

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
