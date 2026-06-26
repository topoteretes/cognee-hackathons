"""Pre-seed canonical Person nodes from the Slack workspace user list.

Goal: every real human in the workspace exists as exactly one Person
node in the graph, keyed by email. After this seed step, mentions
resolved to ``email`` form in thread text land on these canonical
nodes instead of producing duplicates.

Run before any thread ingestion. The cognee server treats
``add_data_points`` as idempotent (re-running with the same
identifiers is a no-op), so this is safe to call repeatedly.
"""

from __future__ import annotations

import logging
import os
from typing import AsyncIterator

from slack_sdk.web.async_client import AsyncWebClient

from .schema import Person

log = logging.getLogger(__name__)


async def slack_people() -> AsyncIterator[Person]:
    """Yield one Person per non-bot, non-deleted user in the workspace."""
    client = AsyncWebClient(token=os.environ["SLACK_BOT_TOKEN"])
    cursor: str | None = None
    while True:
        resp = await client.users_list(limit=200, cursor=cursor)
        for u in resp.get("members", []):
            if u.get("is_bot") or u.get("deleted") or u.get("id") == "USLACKBOT":
                continue
            profile = u.get("profile") or {}
            email = profile.get("email")
            if not email:
                continue
            name = (
                profile.get("real_name_normalized")
                or profile.get("display_name_normalized")
                or u.get("real_name")
                or u.get("name")
                or email
            )
            yield Person(email=email, name=name, slack_id=u.get("id"))
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            return


async def seed_people() -> list[Person]:
    """Fetch all workspace users and persist them as Person DataPoints."""
    from cognee.tasks.storage import add_data_points

    people: list[Person] = [p async for p in slack_people()]
    if not people:
        log.info("people: no users to seed")
        return []
    log.info("people: seeding %d canonical persons", len(people))
    await add_data_points(people)
    return people


async def build_lookup() -> dict[str, str]:
    """Return ``{slack_user_id: email}`` for mention resolution."""
    lookup: dict[str, str] = {}
    async for p in slack_people():
        if p.slack_id:
            lookup[p.slack_id] = p.email
    return lookup
