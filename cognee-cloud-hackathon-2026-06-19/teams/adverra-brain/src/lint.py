"""Lint — keep the wiki coherent (Karpathy's third operation).

Asks the brain, through the linter skill, to surface duplicates, conflicting
facts, stale entries (e.g. the deprecated Tango processor), and coverage gaps.

Run:
    python -m src.lint
"""

from __future__ import annotations

import asyncio

from .query import ask

LINT_PROMPT = (
    "Act as the Company Brain linter. Review the Cashly/Adverra knowledge for: "
    "(1) duplicate facts, (2) conflicting numbers or policies, "
    "(3) stale entries tied to deprecated systems or past dates, "
    "(4) coverage gaps. List each issue with a recommended action."
)


async def lint() -> None:
    ans = await ask(LINT_PROMPT, skills=["linter"])
    print("\n=== Company Brain — Lint Report ===\n")
    print(ans.text or "(no issues reported)")


if __name__ == "__main__":
    asyncio.run(lint())
