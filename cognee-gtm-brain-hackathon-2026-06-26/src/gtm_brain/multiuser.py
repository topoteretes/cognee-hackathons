"""Per-user data isolation and sharing on top of the GTM brain.

Cognee has multi-user access control built in: every dataset is *owned*
by a user, lives in its own graph/vector database, and is reachable by
another user only through an explicit permission (ACL). This module
wires the GTM-brain ingest into that model so each user gets an
**isolated** brain, and adds the **sharing** step that grants another
user read access.

Turn it on by setting ``ENABLE_BACKEND_ACCESS_CONTROL=true`` *before*
any cognee call (see :func:`enable_access_control`). With it on:

- ``ingest_brain_for_user(root, dataset, user)`` seeds the structured
  GTM nodes into that user's dataset DB context and cognifies the
  conversations as that user — nobody else can see them.
- ``recall_as(user, query, [dataset])`` only returns hits from datasets
  the user is authorized to read.
- ``share_dataset(owner, recipient, dataset, "read")`` adds an ACL so
  the recipient's recall now spans the owner's dataset too.

The two GTM identity anchors (``Person.email``, ``Company.domain``)
still apply *within* each user's graph; sharing makes a second graph
visible without merging the underlying stores.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from .cognee_client import _extraction_prompt
from .gtm_people import Roster
from .schema import Thread
from .sources.gtm_files import GTMBrainSource

log = logging.getLogger(__name__)

DEFAULT_DEMO_PASSWORD = "hackathon-demo-pw"


def enable_access_control() -> None:
    """Switch cognee into multi-user access-control mode.

    Must run before the first cognee operation in the process. Idempotent.
    """
    os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"
    log.info("multiuser: ENABLE_BACKEND_ACCESS_CONTROL=true")


@dataclass(slots=True)
class IngestCounts:
    dataset: str = ""
    companies: int = 0
    people: int = 0
    events: int = 0
    deals: int = 0
    signals: int = 0
    calendar: int = 0
    icps: int = 0
    threads: int = 0
    failures: int = 0
    extra: dict = field(default_factory=dict)


async def get_or_create_user(email: str, password: str = DEFAULT_DEMO_PASSWORD):
    """Return the cognee user for ``email``, creating it if necessary."""
    from cognee.modules.users.methods import create_user, get_user_by_email

    user = await get_user_by_email(email)
    if user is not None:
        return user
    user = await create_user(email, password, is_superuser=False)
    log.info("multiuser: created user %s", email)
    return user


async def _resolve_owned_dataset(dataset_name: str, user):
    """Get the user's dataset by name, creating it (owned by user) if absent."""
    from cognee.modules.data.methods import (
        create_authorized_dataset,
        get_authorized_existing_datasets,
    )

    existing = await get_authorized_existing_datasets([dataset_name], "write", user)
    if existing:
        return existing[0]
    return await create_authorized_dataset(dataset_name, user)


async def ingest_brain_for_user(root: str | Path, dataset_name: str, user) -> IngestCounts:
    """Ingest a GTM brain folder into a dataset owned by ``user``.

    Structured nodes are seeded inside the dataset's DB context so they
    land in the user's isolated store; conversations are then cognified
    as that user and link onto them.
    """
    import cognee
    from cognee.context_global_variables import set_database_global_context_variables
    from cognee.tasks.storage import add_data_points

    root = Path(root)
    src = GTMBrainSource(root, roster=Roster())
    companies = src.companies()
    people = src.people()
    events = src.events()
    deals = src.deals()
    signals = src.signals()
    calendar = src.calendar_events()
    icps = src.icps()
    docs = list(src.conversation_docs())

    counts = IngestCounts(dataset=dataset_name)
    dataset = await _resolve_owned_dataset(dataset_name, user)
    owner_id = getattr(dataset, "owner_id", None) or user.id

    # Phase 1 — structured canonical nodes, inside the dataset DB context.
    async with set_database_global_context_variables(dataset.id, owner_id):
        await add_data_points(companies + people + events)
        await add_data_points(deals + signals + calendar + icps)
    counts.companies = len(companies)
    counts.people = len(people)
    counts.events = len(events)
    counts.deals = len(deals)
    counts.signals = len(signals)
    counts.calendar = len(calendar)
    counts.icps = len(icps)

    # Phase 2 — stage conversations as this user, then cognify once.
    staged = 0
    for doc in docs:
        try:
            await cognee.add(
                doc.body(),
                dataset_name=dataset_name,
                user=user,
                node_set=doc.tags(),
            )
            staged += 1
        except Exception as exc:
            counts.failures += 1
            log.warning("multiuser: stage failed %s: %s", doc.doc_id, exc)

    if staged:
        try:
            await cognee.cognify(
                datasets=[dataset_name],
                user=user,
                graph_model=Thread,
                custom_prompt=_extraction_prompt(),
            )
            counts.threads = staged
        except Exception as exc:
            counts.failures += 1
            log.warning("multiuser: cognify failed for %s: %s", dataset_name, exc)

    log.info(
        "multiuser: %s ingested into '%s' — companies=%d deals=%d threads=%d",
        getattr(user, "email", user),
        dataset_name,
        counts.companies,
        counts.deals,
        counts.threads,
    )
    return counts


async def share_dataset(owner, recipient, dataset_name: str, permission: str = "read") -> None:
    """Grant ``recipient`` ``permission`` on ``owner``'s dataset.

    ``owner`` must hold the ``share`` permission on the dataset (the
    creator always does). Valid permissions: read / write / delete / share.
    """
    from cognee.modules.data.methods import get_authorized_existing_datasets
    from cognee.modules.users.permissions.methods import (
        authorized_give_permission_on_datasets,
    )

    shareable = await get_authorized_existing_datasets([dataset_name], "share", owner)
    if not shareable:
        raise ValueError(
            f"{getattr(owner, 'email', owner)} cannot share '{dataset_name}' "
            "(not found or missing 'share' permission)"
        )
    dataset = shareable[0]
    await authorized_give_permission_on_datasets(
        recipient.id, [dataset.id], permission, owner.id
    )
    log.info(
        "multiuser: shared '%s' (%s) %s -> %s",
        dataset_name,
        permission,
        getattr(owner, "email", owner),
        getattr(recipient, "email", recipient),
    )


async def _readable_datasets(user, names: list[str] | None = None):
    """Dataset objects ``user`` can read (own + shared).

    Resolving by *name* through cognee's own helper only matches datasets
    the user owns, so a shared dataset is invisible by name. We instead
    list *all* readable datasets (which includes shared ones, by id) and
    filter by name ourselves — that's what makes a shared brain reachable.
    """
    from cognee.modules.data.methods import get_authorized_existing_datasets

    readable = await get_authorized_existing_datasets(None, "read", user)
    if names is None:
        return readable
    wanted = {n.lower() for n in names}
    return [d for d in readable if (getattr(d, "name", "") or "").lower() in wanted]


async def list_readable_datasets(user) -> list[str]:
    """Names of every dataset ``user`` can currently read (own + shared)."""
    return [getattr(d, "name", str(d.id)) for d in await _readable_datasets(user)]


async def recall_as(user, query: str, datasets: list[str] | None = None, *, top_k: int = 5):
    """Recall scoped to ``user``'s permissions.

    When ``datasets`` names are given, they are resolved to ids through the
    user's full readable set — which includes datasets shared with them.
    If the user has no read access to any of the named datasets, returns
    ``[]`` rather than erroring: that empty result *is* the isolation
    guarantee (before a share) made visible.
    """
    import cognee

    kwargs: dict = {"top_k": top_k, "user": user}
    if datasets:
        matched = await _readable_datasets(user, datasets)
        if not matched:
            return []  # no access -> isolated
        kwargs["dataset_ids"] = [d.id for d in matched]
    return await cognee.recall(query, **kwargs)


async def visualize_user_dataset(output_path: str, dataset_name: str, user) -> str:
    """Render the graph of one of ``user``'s readable datasets to HTML.

    Uses the multi-user visualization path with a single (user, dataset)
    pair — under access control ``visualize_graph`` alone can't pick the
    right per-dataset database, so this is the correct entry point.
    """
    from cognee.api.v1.visualize import visualize_multi_user_graph

    matched = await _readable_datasets(user, [dataset_name])
    if not matched:
        raise ValueError(f"{getattr(user, 'email', user)} cannot read '{dataset_name}'")
    await visualize_multi_user_graph([(user, matched[0])], output_path)
    return output_path


async def visualize_all_readable(output_path: str, user) -> str:
    """Render *every* dataset ``user`` can read into one HTML view.

    Before a share this shows only the user's own brain; after a share it
    spans the owner's dataset too — the visual proof that sharing widened
    what the user can see.
    """
    from cognee.api.v1.visualize import visualize_multi_user_graph
    from cognee.modules.data.methods import get_authorized_existing_datasets

    datasets = await get_authorized_existing_datasets(None, "read", user)
    if not datasets:
        raise ValueError(f"{getattr(user, 'email', user)} has no readable datasets")
    await visualize_multi_user_graph([(user, ds) for ds in datasets], output_path)
    return output_path
