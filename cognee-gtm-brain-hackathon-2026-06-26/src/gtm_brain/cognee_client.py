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
- Set Thread.title from the markdown H1 line at the top of the document, without the leading "#".
- Set Thread.source from the "Source:" metadata line.
- Set Thread.doc_id from the "Document ID:" metadata line.
- Set Thread.channel from the "Container:" metadata line.
- Set Thread.started_at from the "Started at:" metadata line.
- Preserve every line under the transcript as a Message node. Do not summarize away, merge away, or omit short greetings, short acknowledgements, or standalone reports.
- For each Message, keep the exact speaker identifier, exact timestamp, and exact text from the transcript line.
- Create Person nodes with both email and name when a People section provides "Name <email>". If only an email is available, use that email as both email and name.
- If a message reports a bug, problem, unexpected behavior, broken flow, regression, or error, create an Issue node and link it from that Message through reports.
- For Issue nodes, preserve the concrete reported behavior in observed_behavior. Example: "remember with node sets keeps extracting everything".
- If a message asks for help or asks what something is about, create a Question node and link it from that Message through raises.
- If a later message acknowledges, promises to investigate, or proposes a call, preserve it as its own Message and connect it to the same Thread context.
- Prefer exact source text over inferred summaries. Derived Topic, Question, Decision, and Issue nodes are allowed, but source Message nodes are mandatory.

GTM linking rules (for sponsor/speaker conversations):
- If the conversation is about an external company (an "account:" or "company:<domain>" tag is present, or a speaker's email domain is not gtm-week.com), set Thread.company with that company's name and domain. Use the domain from the "company:" tag when present, otherwise the non-gtm-week.com email domain of the external participant. Do NOT invent a domain.
- Set Thread.event to the GTM Tech Week edition the conversation concerns: "GTM Tech Week London 2027" for sponsorship/keynote planning, "Warsaw 2026" for the post-event debrief.
- Treat a sponsorship blocker, format objection, date clash, or "do not approach" constraint as an Issue.

Return data that conforms to the provided graph model.
"""


def _dataset() -> str:
    return os.environ.get("COGNEE_DATASET", "gtm_brain")


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


async def write(doc: Doc, *, dataset_name: str | None = None) -> None:
    """v0 path: free-form remember with node_set tags."""
    await cognee.remember(
        doc.body(),
        dataset_name=dataset_name or _dataset(),
        node_set=doc.tags(),
    )


async def add_doc(
    doc: Doc,
    extra_tags: list[str] | None = None,
    *,
    dataset_name: str | None = None,
) -> None:
    """Stage a doc's transcript into the dataset without cognifying yet."""
    ds = dataset_name or _dataset()
    tags = doc.tags() + (extra_tags or [])
    await cognee.add(doc.body(), dataset_name=ds, node_set=tags)


async def cognify_threads(*, dataset_name: str | None = None) -> None:
    """Run cognify over the dataset constrained to the Thread schema."""
    ds = dataset_name or _dataset()
    await cognee.cognify(
        datasets=[ds],
        graph_model=Thread,
        custom_prompt=_extraction_prompt(),
    )


async def write_typed(
    doc: Doc,
    extra_tags: list[str] | None = None,
    *,
    dataset_name: str | None = None,
) -> None:
    """v2 path: add + cognify constrained to the Thread schema.

    Pre-seeded Person/Company nodes (see ``people.seed_people`` and
    ``ingest.ingest_gtm_brain``) anchor the extracted speakers, mentions
    and accounts, so this call produces typed Message nodes linked to the
    canonical Persons and the Thread linked to the canonical Company
    instead of creating duplicates.
    """
    await add_doc(doc, extra_tags, dataset_name=dataset_name)
    await cognify_threads(dataset_name=dataset_name)


async def seed_points(points: list, *, label: str = "data points") -> int:
    """Persist canonical DataPoints (idempotent by identity_fields).

    Seeding Company/Person/Deal/Signal/CalendarEvent/ICP nodes *before*
    cognifying conversations is what fuses the two graphs: cognify then
    attaches messages and threads onto these existing nodes by email /
    domain rather than spawning duplicates.
    """
    points = [p for p in points if p is not None]
    if not points:
        return 0
    from cognee.tasks.storage import add_data_points

    await add_data_points(points)
    log.info("seeded %d %s", len(points), label)
    return len(points)


async def recall(
    query: str,
    *,
    node_set: list[str] | None = None,
    datasets: list[str] | None = None,
    top_k: int = 5,
    only_context: bool = False,
) -> list[dict]:
    kwargs = {"top_k": top_k, "datasets": datasets or [_dataset()], "only_context": only_context}
    if node_set:
        kwargs["scope"] = node_set
    return await cognee.recall(query, **kwargs)


async def visualize_graph(output_path: str, *, dataset: str | None = None) -> str:
    """Write Cognee's graph visualization to an HTML file.

    When ``dataset`` is provided, render the graph from that dataset's database
    context. Without it, render all datasets the current user can read.
    """
    from cognee.context_global_variables import set_database_global_context_variables
    from cognee.api.v1.visualize import visualize_multi_user_graph
    from cognee.modules.data.methods import get_authorized_existing_datasets
    from cognee.modules.users.methods import get_default_user

    user = await get_default_user()

    if dataset is None:
        datasets = await get_authorized_existing_datasets(None, "read", user)
        if not datasets:
            raise ValueError("No readable Cognee datasets found. Run ingest before visualize.")
        await visualize_multi_user_graph([(user, ds) for ds in datasets], output_path)
        return output_path

    datasets = await get_authorized_existing_datasets([dataset], "read", user)
    if not datasets:
        raise ValueError(f"Dataset not found or not readable: {dataset}")

    dataset_obj = datasets[0]
    owner_id = getattr(dataset_obj, "owner_id", None) or user.id
    async with set_database_global_context_variables(dataset_obj.id, owner_id):
        await cognee.visualize_graph(output_path)
    return output_path
