"""Thin wrapper around the Cognee remember/recall surface.

Keeps the rest of the codebase free of cognee imports and gives us one
place to swap the backend, add retries, or tee writes for tests.

Two write paths:
- ``write(doc)`` — legacy free-form ingest used by v0. Calls
  ``cognee.remember(text, dataset=…)`` and lets the default extractor
  populate generic Entity nodes. Kept for backwards compatibility.
- ``write_typed(doc, tags)`` — v2 ingest. Adds the doc text to the
  dataset and runs cognify constrained to the :class:`Thread` schema,
  producing typed Person/Message/Topic/Decision nodes instead of
  generic Entity. Tags ride as ``node_set`` so downstream filters can
  scope queries by source/channel/product/client/domain.
"""

from __future__ import annotations

import logging
import os

import cognee

from .normalize import Doc
from .schema import Thread

log = logging.getLogger(__name__)

_EXTRACTION_PROMPT = """Extract a company conversation graph from the provided transcript.

The graph model is Thread with nested Person, Message, Topic, Question, Decision, and Issue nodes.

Mandatory extraction rules:
- Preserve every line under the transcript as a Message node. Do not summarize away, merge away, or omit short greetings, short acknowledgements, or standalone reports.
- For each Message, keep the exact speaker identifier, exact timestamp, and exact text from the transcript line.
- Create Person nodes with both email and name when a People section provides "Name <email>". If only an email is available, use that email as both email and name.
- If a message reports a bug, problem, unexpected behavior, broken flow, regression, or error, create an Issue node and link it from that Message through reports.
- For Issue nodes, preserve the concrete reported behavior in observed_behavior. Example: "remember with node sets keeps extracting everything".
- If a message asks for help or asks what something is about, create a Question node and link it from that Message through raises.
- If a later message acknowledges, promises to investigate, or proposes a call, preserve it as its own Message and connect it to the same Thread context.
- Prefer exact source text over inferred summaries. Derived Topic, Question, Decision, and Issue nodes are allowed, but source Message nodes are mandatory.

Return data that conforms to the provided graph model.
"""


def _dataset() -> str:
    return os.environ.get("COGNEE_DATASET", "company_brain")


def _extraction_prompt() -> str:
    return os.environ.get("COGNEE_EXTRACTION_PROMPT", _EXTRACTION_PROMPT)


async def connect() -> None:
    url = os.environ.get("COGNEE_SERVICE_URL", "").strip()
    if not url:
        log.info("cognee: in-process mode (no COGNEE_SERVICE_URL set)")
        return
    api_key = os.environ.get("COGNEE_API_KEY", "").strip() or None
    await cognee.serve(url=url, api_key=api_key)
    log.info("cognee: connected to %s", url)


async def write(doc: Doc) -> None:
    """v0 path: free-form remember with node_set tags."""
    await cognee.remember(
        doc.body(),
        dataset_name=_dataset(),
        node_set=doc.tags(),
    )


async def write_typed(doc: Doc, extra_tags: list[str] | None = None) -> None:
    """v2 path: add + cognify constrained to the Thread schema.

    Pre-seeded Person nodes (see ``people.seed_people``) anchor the
    extracted speakers/mentions, so this call produces typed Message
    nodes linked to the canonical Persons instead of new duplicates.
    """
    ds = _dataset()
    tags = doc.tags() + (extra_tags or [])
    await cognee.add(
        doc.body(),
        dataset_name=ds,
        node_set=tags,
    )
    await cognee.cognify(
        datasets=[ds],
        graph_model=Thread,
        custom_prompt=_extraction_prompt(),
    )


async def recall(
    query: str,
    *,
    node_set: list[str] | None = None,
    top_k: int = 5,
    only_context: bool = False,
) -> list[dict]:
    kwargs = {"top_k": top_k, "datasets": [_dataset()], "only_context": only_context}
    if node_set:
        kwargs["scope"] = node_set
    return await cognee.recall(query, **kwargs)
