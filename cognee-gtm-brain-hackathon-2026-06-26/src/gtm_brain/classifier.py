"""Two-axis LLM classifier for routing threads.

Each thread gets tagged with up to one ``product`` (which thing we
built), up to one ``client`` (which external party), and exactly one
``domain`` (kind of conversation). The classifier picks from fixed
vocabularies so the resulting tags are deterministic — unknown labels
fall through to ``null`` and ``domain:misc``.

This is what lets a thread in #adhoc about an Acme cloud bug get tagged
``product:cloud client:acme domain:technical`` and connect into the
same subgraphs as native #ext-acme-cognee + cloud-engineering threads.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from openai import AsyncOpenAI

log = logging.getLogger(__name__)

# In the GTM brain, "product" is the event surface/track a thread is about.
PRODUCTS = [
    "sponsorship-track",
    "keynote",
    "clay-club",
    "agenda",
    "event-ops",
]
# Accounts that show up in the GTM dataset. Extend from attio_companies.csv.
CLIENTS = [
    "clay",
    "pavilion",
    "cognism",
    "apollo",
    "woodpecker",
    "brand24",
    "surfer",
    "livespace",
]
DOMAINS = ["sponsorship", "speaking", "event-ops", "internal", "social", "misc"]


_PROMPT = """Classify this GTM conversation (Slack thread, meeting, or email) for a knowledge graph.

Return ONLY a JSON object with these fields:
- product: one of [{products}], or null if no specific event surface is the subject
- client:  one of [{clients}], or null if not about a specific external company
- domain:  one of [{domains}]

Use "sponsorship" for selling/scoping sponsorship, packages, booths, or co-created tracks.
Use "speaking" for recruiting speakers/keynotes or speaker logistics.
Use "event-ops" for venue, agenda, ticketing, pricing, and run-of-show.
Use "internal" for team debriefs and planning with no external party.
Use "social" for intros, chitchat, FYIs.
Use "misc" if you can't classify cleanly.

Conversation:
{transcript}

JSON:"""


@dataclass(slots=True, frozen=True)
class Routing:
    product: str | None
    client: str | None
    domain: str

    def tags(self) -> list[str]:
        out: list[str] = [f"domain:{self.domain}"]
        if self.product:
            out.append(f"product:{self.product}")
        if self.client:
            out.append(f"client:{self.client}")
        return out


class Classifier:
    """Async LLM classifier. Shares one OpenAI client across calls."""

    def __init__(self, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=os.environ["LLM_API_KEY"])
        self._model = model or os.environ.get("CLASSIFIER_MODEL", "gpt-4o-mini")

    async def classify(self, transcript: str) -> Routing:
        prompt = _PROMPT.format(
            products=", ".join(PRODUCTS),
            clients=", ".join(CLIENTS),
            domains=", ".join(DOMAINS),
            transcript=transcript[:6000],
        )
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content or "{}")
        except Exception as e:
            log.warning("classifier failed (%s): %s", type(e).__name__, e)
            return Routing(None, None, "misc")

        product = _normalize(data.get("product"), PRODUCTS)
        client = _normalize(data.get("client"), CLIENTS)
        domain = _normalize(data.get("domain"), DOMAINS) or "misc"
        return Routing(product=product, client=client, domain=domain)


def _normalize(value, allowed: list[str]) -> str | None:
    if not value or value == "null":
        return None
    v = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return v if v in allowed else None
