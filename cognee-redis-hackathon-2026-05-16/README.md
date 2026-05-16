# Cognee × Redis Hackathon — 2026-05-16

🧠 **AI-Memory Hackathon: Building your own Agent LLM Wiki** 🚀

> "Instead of just retrieving from raw documents at query time, the LLM
> incrementally builds and maintains a persistent wiki." — Andrej Karpathy

Karpathy recently popularised the idea of an LLM Wiki. In this hackathon you
will extend that idea and build one together with us, using Cognee's
open-source memory engine and Redis.

Karpathy's note for reference:
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## What You Build

An **LLM Knowledge Wiki** powered by Cognee memory. Your wiki must support
three base operations:

1. **Ingest** — pull raw documents, conversations, or runs into the wiki.
2. **Query + Self-improve** — answer questions, and use feedback from each
   query to grow and refine the wiki.
3. **Lint** — keep the wiki coherent: deduplicate, resolve conflicts, and
   prune stale entries.

The goal is not just retrieval — it is a wiki that gets smarter the more it
is used.

## Memory Architecture — Where Redis Fits

Your wiki runs on a **two-tier memory** model:

```text
                    [ agent / user ]
                          │
                          ▼
          ┌─────────────────────────────────┐
          │  Redis — session memory          │   fast, ephemeral
          │  (working scratchpad, recent     │   per-conversation
          │   conversations, raw events)     │
          └────────────────┬─────────────────┘
                           │  distillation
                           ▼
          ┌─────────────────────────────────┐
          │  Cognee — permanent memory       │   structured, durable
          │  (knowledge graph, embeddings,   │   cross-session
          │   skills, summaries)             │
          └─────────────────────────────────┘
```

- **Redis is the agent's session memory.** The agent loads recent data into
  Redis as it works: raw events, user turns, intermediate observations. This
  is the hot, fast scratchpad.
- **Cognee is the permanent memory.** Session content is distilled into the
  knowledge graph — entities, relationships, summaries, and skills — so it
  can be recalled across sessions and refined over time.
- **The self-improvement loop lives in this distillation step.** What gets
  promoted from Redis into the graph, how it's structured, and how feedback
  rewrites it, is the core of your wiki design.

In code, this maps directly onto cognee's `session_id` parameter:

```python
# Goes to Redis session memory — fast cache, syncs to graph in background
await cognee.remember("user just asked about retention", session_id="chat_1")

# Goes straight to the permanent knowledge graph
await cognee.remember("Retention is calculated as ...")

# Recall queries session memory first, falls through to the graph
await cognee.recall("what did the user ask?", session_id="chat_1")
```

**This Redis-as-session-memory pattern is the core piece of the hackathon.**
Judges will want to see how you use it: what your agent puts into session
memory, how it decides what to distill into the graph, and how distillation
quality improves run over run.

## Prizes — $1,500+ Cash Pool

| Place | Prize |
|-------|-------|
| 🥇 1st | $800 cash |
| 🥈 2nd | $500 cash |
| 🥉 3rd | $200 cash |

## Demo Format

You will have **3 minutes** to stand out:

- Present your idea and explain how you leverage agent self-improvement.
- Run a live demo that showcases your agent in action.

## Schedule

| Time | What |
|------|------|
| 12:00 PM | Doors open + networking |
| 12:30 PM | Opening remarks + partner demos |
| 1:00 PM | Hacking begins |
| 4:30 PM | Project submission deadline — finalists selected |
| 5:00 PM | Finalist presentations & judging |
| 5:30 PM | Awards ceremony |
| 6:00 PM | Event wrap-up & doors close |

## Setup

> **You do not need to bring API keys or accounts.** We provide the LLM API
> key (OpenAI) and any other event-specific credentials at kickoff. Everything
> below is so you know how to wire what we hand you into your project — not
> a list of things to sign up for in advance.

### Prerequisites

- Python 3.10 – 3.14
- Docker (for Redis)
- An LLM API key — **provided by us at kickoff** (you can also bring your own
  from any [supported provider](https://docs.cognee.ai/setup-configuration/llm-providers))

### 1. Install Cognee

```bash
uv venv && source .venv/bin/activate
uv pip install "cognee[redis]"
```

### 2. Configure the LLM

We hand out an `LLM_API_KEY` at kickoff — export it in your shell:

```bash
export LLM_API_KEY="<key-we-give-you-at-the-event>"
```

Or drop it into a local `.env` based on cognee's [`.env.template`](https://github.com/topoteretes/cognee/blob/main/.env.template).
Prefer your own provider? Set `LLM_PROVIDER` / `LLM_MODEL` per the
[provider docs](https://docs.cognee.ai/setup-configuration/llm-providers).

### 3. Start Redis (session memory)

Redis is the **session-memory layer** — the fast scratchpad your agent writes
into during a conversation, before content is distilled into the permanent
graph. Cognee picks it up automatically when `REDIS_URL` is set and any
`cognee.remember(..., session_id=...)` call routes there.

```bash
docker run -p 6379:6379 redis:latest
export REDIS_URL=redis://localhost:6379
```

### 4. Run the Pipeline

Cognee's API exposes four operations — `remember`, `recall`, `forget`, and
`improve`:

```python
import asyncio
import cognee


async def main():
    # Store permanently in the knowledge graph (runs add + cognify + improve)
    await cognee.remember("Cognee turns documents into AI memory.")

    # Store in session memory (fast cache, syncs to graph in background)
    await cognee.remember(
        "User prefers detailed explanations.",
        session_id="chat_1",
    )

    # Query with auto-routing (picks best search strategy automatically)
    results = await cognee.recall("What does Cognee do?")
    for result in results:
        print(result)

    # Query session memory first, fall through to graph if needed
    results = await cognee.recall(
        "What does the user prefer?",
        session_id="chat_1",
    )
    for result in results:
        print(result)

    # Delete when done
    await cognee.forget(dataset="main_dataset")


if __name__ == "__main__":
    asyncio.run(main())
```

### CLI

The same operations are exposed as a CLI:

```bash
cognee-cli remember "Cognee turns documents into AI memory."
cognee-cli recall "What does Cognee do?"
cognee-cli forget --all
```

Launch the local UI with `cognee-cli -ui` (web app at http://localhost:3000).

### Cognee Cloud (not recommended for this hackathon)

Cognee Cloud does not support the features required for this hackahon ... yet!


## Skills & the Self-Improvement Loop

A **skill** is a small Markdown file that tells the agent how to behave for a
specific task. Skills live in a folder, get ingested into the graph via
`cognee.remember(..., content_type="skills")`, and are selected at query time.
After each run you record a `SkillRunEntry` with a score; cognee turns that
into a **proposal** to rewrite the skill, which you then explicitly **apply**.
That two-step propose-then-apply cycle is what "self-improvement" means in
this hackathon.

### The loop

```text
┌──────────────┐   1. remember(skills)
│  my_skills/  │ ─────────────────────────────┐
└──────────────┘                              ▼
                                       ┌───────────────┐
2. search(AGENTIC_COMPLETION,          │   Cognee      │
   skills=[...], session_id=...)  ───▶ │  knowledge    │
                                       │     graph     │
3. score the run yourself              └──────┬────────┘
                                              │
4. remember(SkillRunEntry, ..., apply=False)  │  proposes
   ─────────────────────────────────────────▶ │  a SKILL.md
                                              │  rewrite
5. improve_skill(proposal_id, apply=True)     │
   ─────────────────────────────────────────▶ │  applies it
                                       ┌──────▼────────┐
                                       │  improved     │
                                       │   SKILL.md    │
                                       └───────────────┘
```

### Folder layout

```text
my_skills/
  code-review/
    SKILL.md
```

`my_skills/code-review/SKILL.md`:

```markdown
---
description: Review code changes for bugs, regressions, and missing tests.
allowed-tools: memory_search
---

# Instructions

Read the diff carefully. Report concrete issues first, with file paths and
line references when available.
```

A starter version is at
[`my_skills/code-review/SKILL.md`](./my_skills/code-review/SKILL.md) — copy
it, fork it, or replace it with your own. Real wikis will usually have
several skills (one to extract, one to evaluate, one to write feedback, ...).

### Run the loop from Python

```python
import asyncio
from uuid import UUID

import cognee
from cognee import SearchType
from cognee.memory import SkillRunEntry
from cognee.modules.engine.operations.setup import setup
from cognee.modules.memify.skill_improvement import improve_skill
from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
    resolve_authorized_user_datasets,
)

DATASET = "my-wiki"
SESSION = "wiki-session-1"


async def main():
    # Fresh slate — drop these two prune calls if you want to keep prior runs.
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()

    # 1. Ingest skills into the graph.
    remembered = await cognee.remember(
        "./my_skills",
        dataset_name=DATASET,
        content_type="skills",
    )
    dataset_id = UUID(remembered.dataset_id)
    user, datasets = await resolve_authorized_user_datasets(dataset_id)
    dataset = datasets[0]

    # 2. Run the agent against the skills. session_id routes working
    #    memory to Redis. Ask the agent to return a JSON score in its answer.
    answer = await cognee.search(
        "Review the current auth changes. Return JSON with a score 0..1.",
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=DATASET,
        skills=["code-review"],
        max_iter=6,
        session_id=SESSION,
    )

    # 3. Score the run. In real life: parse `answer`, run an eval, etc.
    score = 0.3
    skill_to_improve = "code-review"

    # 4. Record feedback. apply=False -> propose a rewrite, don't change the
    #    skill yet. score_threshold sets when a proposal is generated.
    proposal_result = await cognee.remember(
        SkillRunEntry(
            selected_skill_id=skill_to_improve,
            task_text="Review the current auth changes",
            result_summary="Review missed a dataset boundary bug.",
            success_score=score,
            feedback=-1.0 if score < 0.7 else 1.0,
        ),
        dataset_name=DATASET,
        session_id=SESSION,
        skill_improvement={
            "skill_name": skill_to_improve,
            "apply": False,
            "score_threshold": 0.9,
        },
    )

    # 5. Apply the proposal explicitly.
    proposal_id = next(
        item["proposal_id"]
        for item in proposal_result.items
        if item.get("kind") == "skill_improvement_proposal"
    )
    await improve_skill(
        skill_to_improve,
        dataset=dataset,
        user=user,
        proposal_id=proposal_id,
        apply=True,
    )


asyncio.run(main())
```

What the knobs do:

- **`session_id`** — routes working memory for this run to Redis. Different
  sessions stay isolated; distillation into the graph happens when you call
  `cognee.remember(...)` without a `session_id` (or via the background sync).
- **`max_iter`** — caps how many agent reasoning steps run before returning.
- **`score_threshold`** (in `skill_improvement`) — only generate a proposal
  when the run score falls *below* this value. Raise it to be aggressive
  about improvement; lower it to only react to clear failures.
- **`apply=False`** — propose without rewriting. Inspect the diff, then call
  `improve_skill(..., apply=True)` to actually update the skill.

A full multi-skill version of this loop (three cooperating skills, JSON
parsing, before/after skill bodies) lives in the cognee repo at
[`examples/demos/skill_feedback_loop/skill_feedback_loop_demo.py`](https://github.com/topoteretes/cognee/tree/main/examples/demos/skill_feedback_loop).

## Other Ways to Run Cognee

| What | How | When to use |
|------|-----|-------------|
| Python SDK | `import cognee` | Building your wiki / agent logic |
| CLI | `cognee-cli remember / recall / forget` | Smoke-tests, ad-hoc ingestion |
| Local UI | `cognee-cli -ui` → http://localhost:3000 | Inspecting the graph visually |
| Cognee Cloud | `await cognee.serve(url=..., api_key=...)` | Skipping infra during the event |
| Claude Code plugin | [`cognee-integrations`](https://github.com/topoteretes/cognee-integrations/tree/main/integrations/claude-code) | Giving Claude Code persistent memory |
| Examples | [`examples/`](https://github.com/topoteretes/cognee/tree/main/examples) in the cognee repo | Reference pipelines & demos |

## Submission

Each team submits:

- a short writeup of the idea and self-improvement loop
- the wiki implementation (code + skills, if any)
- before/after evidence that the wiki improved from feedback
- a 3-minute demo

Use [`templates/SUBMISSION.md`](./templates/SUBMISSION.md) — copy it into your
team folder or PR description and fill it in.

## Resources

- [Cognee Documentation](https://docs.cognee.ai/)
- [Karpathy on LLM Wikis](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Redis Documentation](https://redis.io/docs/)
- [Discord](https://discord.gg/NQPKmU5CCg)

---

*Full challenge brief, starter skills, and submission template will land in
this folder ahead of the event.*
