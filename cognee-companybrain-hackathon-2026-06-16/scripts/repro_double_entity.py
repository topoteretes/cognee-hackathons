#!/usr/bin/env python3
"""Minimal reproduction of the double-entity-extraction issue.

Loads the four hand-prepared transcripts from ``sample_data/`` and
ingests them via the v2 path (``cognee.add`` + ``cognee.cognify`` with
``graph_model=Thread``). After ingestion it inspects the dataset's
EntityType and Entity collections and prints how many entries we see
for Veljko and Milenko — they should each end up as exactly one
canonical Person node, but you'll see several Entity rows per email.

Usage:
    export LLM_API_KEY=sk-...          # OpenAI key Cognee uses too
    export COGNEE_API_KEY=...          # if running against a server
    export COGNEE_SERVICE_URL=http://localhost:8000  # optional
    python scripts/repro_double_entity.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import cognee  # noqa: E402

from company_brain.normalize import Doc, Utterance  # noqa: E402
from company_brain.schema import Thread  # noqa: E402

log = logging.getLogger(__name__)

SAMPLE_DIR = Path(__file__).parent.parent / "sample_data"
DATASET = os.environ.get("REPRO_DATASET", "repro_double_entity")


def _doc_from_file(path: Path) -> Doc:
    """Wrap a sample file's text as a Doc so we go through the same
    ``write_typed`` path the v2 ingest uses."""
    text = path.read_text(encoding="utf-8")
    title = text.splitlines()[0].lstrip("# ").strip() if text else path.stem
    now = datetime.now(timezone.utc)
    return Doc(
        source="sample",
        doc_id=path.stem,
        title=title,
        container="brain-project" if path.name.startswith("slack") else "granola",
        started_at=now,
        # The whole file body — already in transcript form — rides as one
        # synthetic Utterance so write_typed treats it identically to a
        # real Slack thread or Granola meeting.
        utterances=[Utterance(speaker="sample-loader", timestamp=now, text=text)],
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    url = os.environ.get("COGNEE_SERVICE_URL", "").strip()
    if url:
        await cognee.serve(url=url, api_key=os.environ.get("COGNEE_API_KEY", "") or None)
        log.info("connected to %s", url)
    else:
        log.info("in-process mode (no COGNEE_SERVICE_URL set)")

    files = sorted(SAMPLE_DIR.glob("*.txt"))
    if not files:
        raise SystemExit(f"no sample files in {SAMPLE_DIR}")
    log.info("ingesting %d sample files into dataset=%r", len(files), DATASET)

    for f in files:
        doc = _doc_from_file(f)
        log.info("  add %s (%d chars)", f.name, len(doc.body()))
        await cognee.add(doc.body(), dataset_name=DATASET, node_set=doc.tags())

    log.info("running cognify with graph_model=Thread …")
    await cognee.cognify(datasets=[DATASET], graph_model=Thread)
    log.info("cognify done")

    _inspect_entities()


def _inspect_entities() -> None:
    """Open the dataset's lance.db directly and count Veljko/Milenko entries."""
    import lance

    # Find the dataset directory
    db_root = (
        Path.home()
        / ".cognee-plugin"
        / "venv"
        / "lib"
        / "python3.12"
        / "site-packages"
        / "cognee"
        / ".cognee_system"
        / "databases"
    )
    if not db_root.exists():
        # Fall back to in-process default location
        db_root = (
            Path(cognee.__file__).parent / ".cognee_system" / "databases"
        )
    if not db_root.exists():
        log.warning("could not locate cognee databases at %s", db_root)
        return

    # Find the most recently-modified dataset dir under the agent owner dir
    candidates = []
    for owner_dir in db_root.iterdir():
        if owner_dir.is_dir():
            for child in owner_dir.glob("*.lance.db"):
                candidates.append(child)
    if not candidates:
        log.warning("no lance.db dirs found under %s", db_root)
        return
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    ds_dir = candidates[0]
    log.info("inspecting %s", ds_dir)

    types_path = ds_dir / "EntityType_name.lance"
    ents_path = ds_dir / "Entity_name.lance"

    if types_path.exists():
        types = lance.dataset(str(types_path)).to_table(columns=["payload"]).column("payload").to_pylist()
        labels = sorted({(p.get("text") or "").lower() for p in types if isinstance(p, dict)})
        print(f"\n=== EntityType labels emitted ({len(labels)} distinct) ===")
        for l in labels:
            print(f"  - {l}")

    if not ents_path.exists():
        log.warning("Entity_name.lance not found")
        return
    ents = lance.dataset(str(ents_path)).to_table(columns=["payload"]).column("payload").to_pylist()
    veljko = [p for p in ents if isinstance(p, dict) and "veljko" in (p.get("text", "") or "").lower()]
    milenko = [p for p in ents if isinstance(p, dict) and "milenko" in (p.get("text", "") or "").lower()]

    print(f"\n=== Entity nodes mentioning 'veljko' ({len(veljko)}) ===")
    for e in veljko[:15]:
        print(f"  text={(e.get('text') or '')[:120]!r}")
    print(f"\n=== Entity nodes mentioning 'milenko' ({len(milenko)}) ===")
    for e in milenko[:15]:
        print(f"  text={(e.get('text') or '')[:120]!r}")

    print(
        "\nExpected: 2 Person nodes (veljko@topoteretes.com, milenko@topoteretes.com)."
        f"\nActual:   {len(veljko)} Entity rows for veljko, {len(milenko)} for milenko."
    )


if __name__ == "__main__":
    asyncio.run(main())
