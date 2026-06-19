"""
Lint — the third operation of the Honestel People Brain.

The People team appends notes to a running updates log (data/updates.md). Over
time that log rots: it restates facts already in the curated docs (duplicates),
contradicts them (conflicts), and carries notes that a later note has
superseded (stale). Lint keeps the brain coherent:

  1. An LLM critic reads the curated docs (authoritative) + the updates log and
     returns a structured LintReport: every duplicate / conflict / stale issue,
     each with a resolution.
  2. It reconciles the *graph*: the volatile updates layer lives in its own
     dataset (honestel-updates), so Lint wipes and rebuilds ONLY that layer
     with the cleaned, coherent log — never touching the curated knowledge or
     the self-improved skill.

Run standalone:  python lint.py
Or as a step:    python main.py --lint
"""

import asyncio
import textwrap
from typing import List, Literal

from pydantic import BaseModel

import cognee
from cognee.infrastructure.llm.LLMGateway import LLMGateway
from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
    resolve_authorized_user_datasets,
)

from main import (
    DATA_DIR,
    DATASET,
    UPDATES_DATASET,
    UPDATES_FILE,
    banner,
    ingest,
    run_probe,
)

LINT_PROBE = (
    "What is Honestel's approved 2026 net-new headcount budget (number of hires "
    "and cost cap), and are we currently proceeding with billing-platform hiring? "
    "Answer with the single current truth."
)


class LintIssue(BaseModel):
    issue_type: Literal["duplicate", "conflict", "stale"]
    summary: str
    statements_involved: List[str]
    resolution: str


class LintReport(BaseModel):
    issues: List[LintIssue]
    cleaned_updates_markdown: str


LINT_SYSTEM = textwrap.dedent(
    """
    You are the LINTER for Honestel's People & Talent brain. You are given the
    CURATED DOCS (authoritative baseline truth) and a free-form UPDATES LOG that
    multiple stakeholders append to directly. Each log entry is tagged with the
    author's role in brackets, e.g. [CFO], [VP Eng], [People]. Keep the brain
    coherent by auditing the UPDATES LOG.

    Use the author's role to judge AUTHORITY over a topic:
    - [CFO] / board decisions outrank others on budget, headcount, and cost.
    - [VP Eng] outranks others on engineering staffing and technical decisions.
    - [People] notes are often working assumptions and are the weakest on the
      above topics — a higher-authority entry supersedes them.

    Classify problems in the updates log:
    - "duplicate": a note that merely restates a fact already in the curated docs
      and adds nothing new. Drop it.
    - "conflict": a note that contradicts the curated docs OR another note.
      Resolve by RECENCY + AUTHORITY: the more recent decision from the
      higher-authority role wins (e.g. a [CFO]/board headcount approval beats a
      [People] working assumption and beats the older curated figure). Keep the
      winner as an EXPLICIT superseding statement (e.g. "2026 headcount is now 8
      hires / EUR 950k [CFO, board-approved], superseding the earlier 6 / EUR 720k").
    - "stale": a note that a LATER or higher-authority note has already
      superseded. Drop the superseded one; keep the winning decision.

    Keep genuinely new, still-valid operational notes (with their [role] tag) as-is.

    Return:
    - issues: every problem found, typed, with the statements involved and your
      resolution.
    - cleaned_updates_markdown: the rewritten updates log — duplicates and stale
      notes removed, conflicts expressed as explicit superseding statements,
      valid notes retained. Keep the "# Source: updates.md ..." heading.
    """
).strip()


def _base_docs_text() -> str:
    docs = sorted(p for p in DATA_DIR.glob("*.md") if p.name != UPDATES_FILE)
    return "\n\n".join(p.read_text() for p in docs)


async def analyze() -> LintReport:
    text = (
        "=== CURATED DOCS (authoritative) ===\n"
        + _base_docs_text()
        + "\n\n=== UPDATES LOG (audit this) ===\n"
        + (DATA_DIR / UPDATES_FILE).read_text()
    )
    return await LLMGateway.acreate_structured_output(
        text_input=text, system_prompt=LINT_SYSTEM, response_model=LintReport
    )


async def reconcile(cleaned_markdown: str) -> None:
    """Rebuild ONLY the volatile updates dataset with the cleaned log."""
    user, datasets = await resolve_authorized_user_datasets(UPDATES_DATASET, None)
    dataset = datasets[0]
    await cognee.forget(dataset_id=dataset.id, user=user)
    await cognee.remember(cleaned_markdown, dataset_name=UPDATES_DATASET)
    # Mirror the cleaned log to a file so context retrieval reflects the post-lint state.
    (DATA_DIR / "updates.cleaned.md").write_text(cleaned_markdown)


def print_report(report: LintReport) -> None:
    print(f"Found {len(report.issues)} issue(s):\n")
    for i, issue in enumerate(report.issues, 1):
        print(f"  {i}. [{issue.issue_type.upper()}] {issue.summary}")
        for s in issue.statements_involved:
            print(f"       - {s}")
        print(f"     -> resolution: {issue.resolution}\n")


async def lint_brain(reconcile_graph: bool = True) -> LintReport:
    report = await analyze()
    print_report(report)
    if reconcile_graph:
        await reconcile(report.cleaned_updates_markdown)
        print("Reconciled the updates dataset with the cleaned log.")
    return report


async def demo() -> None:
    await ingest(reset=True)

    banner("LINT — before: the brain has conflicting / stale knowledge")
    print(f"Q: {LINT_PROBE}\n")
    print(await run_probe(LINT_PROBE) or "(no answer)")

    banner("LINT — auditing the updates log")
    report = await lint_brain(reconcile_graph=True)

    banner("LINT — after: the brain answers coherently")
    print(f"Q: {LINT_PROBE}\n")
    print(await run_probe(LINT_PROBE) or "(no answer)")


if __name__ == "__main__":
    asyncio.run(demo())
