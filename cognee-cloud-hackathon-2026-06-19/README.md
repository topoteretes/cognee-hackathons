# Cognee Cloud Hackathon — Build Your Company Brain

📍 **Berlin · 2026-06-19**

🧠 **Company Brain Hackathon: turn your team's scattered knowledge into a brain that gets smarter** 🚀

> "Instead of just retrieving from raw documents at query time, the LLM
> incrementally builds and maintains a persistent wiki." — Andrej Karpathy

Karpathy popularised the idea of an LLM Wiki — a knowledge base the model
grows and maintains for itself. In this hackathon we take that idea and make
it concrete: you will build a **Company Brain**, an LLM knowledge base for a
team or company, on top of Cognee's memory engine — with **Cognee Cloud**
ready whenever you want a managed home for it.

Karpathy's note for reference:
https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## What You Build

A **Company Brain** powered by Cognee memory. Ingest a company's or team's
scattered knowledge — docs, Slack/chat, tickets, code, meeting notes, agent
runs — into a Cognee knowledge base that an agent queries and that
self-improves from feedback. Your brain must support three base operations:

1. **Ingest** — pull raw company knowledge into the brain.
2. **Query + Self-improve** — answer questions, and use feedback from each
   query to grow and refine the brain.
3. **Lint** — keep it coherent: deduplicate, resolve conflicts, and prune
   stale entries.

The goal is not just retrieval — it is a brain that gets smarter the more it
is used.

## Memory Architecture — One Brain, Two Tiers

> 💎 **Cognee Cloud is optional — but it boosts your reward.** Your Company
> Brain runs locally out of the box. Connecting it to **Cognee Cloud** via
> `cognee.serve(...)` is an optional first step that judges reward: there's a
> dedicated **"Best use of Cognee Cloud"** bonus, and Cloud projects start
> ahead on the rubric. We hand every team a dedicated Cloud URL + API key at
> kickoff — there's nothing to set up in advance.

Your brain has two memory tiers — a fast per-conversation scratchpad and a
durable, cross-session knowledge graph. Both live inside the **same cognee
instance**, whether you run it locally (the default) or point it at **Cognee
Cloud**:

```text
                    [ agent / user ]
                          │
                          ▼
   ┌───────────────────────────────────────────────────┐
   │               Your cognee instance                  │
   │      (local by default · Cognee Cloud optional)     │
   │                                                     │
   │   ┌─────────────────────────────────────────────┐  │
   │   │  session memory  (session_id=...)            │  │  fast, ephemeral
   │   │  working scratchpad, recent turns, raw       │  │  per-conversation
   │   │  events                                      │  │
   │   └──────────────────┬──────────────────────────┘  │
   │                      │  distillation                │
   │                      ▼                              │
   │   ┌─────────────────────────────────────────────┐  │
   │   │  permanent graph  (no session_id)            │  │  structured, durable
   │   │  knowledge graph, embeddings, skills,        │  │  cross-session
   │   │  summaries                                   │  │
   │   └─────────────────────────────────────────────┘  │
   └───────────────────────────────────────────────────┘
```

- **Session memory is the agent's scratchpad.** Calls with `session_id=...`
  are the hot, fast, per-conversation tier — raw events, user turns,
  intermediate observations — living inside the Cloud instance.
- **The permanent graph is the durable brain.** Calls without a `session_id`
  are distilled into the knowledge graph — entities, relationships,
  summaries, and skills — so they can be recalled across sessions and refined
  over time.
- **The self-improvement loop lives in this distillation step.** What gets
  promoted from session memory into the permanent graph, how it's structured,
  and how feedback rewrites it, is the core of your Company Brain design — and
  it all happens inside the managed Cognee Cloud instance.

Connect once with `cognee.serve(...)`, then both tiers map onto the
`session_id` parameter:

```python
import cognee

# Point at your team's managed Cognee Cloud instance (handed out at kickoff)
await cognee.serve(url="https://your-instance.cognee.ai", api_key="ck_...")

# Goes straight to the permanent knowledge graph
await cognee.remember("Retention is calculated as ...")

# Goes to session memory inside the Cloud instance — fast, per-conversation
await cognee.remember("user just asked about retention", session_id="chat_1")

# Recall queries session memory first, falls through to the graph
results = await cognee.recall("what did the user ask?", session_id="chat_1")
```

**This distillation pattern is the core piece of the hackathon.** Judges will
want to see how you use it: what your agent puts into session memory, how it
decides what to distill into the permanent graph, and how distillation quality
improves run over run.

## Prizes — 1,200€ Cash Pool

| Place | Prize |
|-------|-------|
| 🥇 1st | 600€ cash |
| 🥈 2nd | 400€ cash |
| 🥉 3rd | 200€ cash |

## Demo Format

You will have **3 minutes** to stand out:

- Present your idea and explain how you leverage agent self-improvement.
- Run a live demo that showcases your Company Brain in action.

## Schedule

All times **Central European Time (CET)**.

| Time | What |
|------|------|
| 5:00 PM | Doors open + networking |
| 5:30 PM | Opening remarks + Cognee Cloud walkthrough |
| 6:00 PM | Hacking begins |
| 9:00 PM | Project submission deadline — finalists selected |
| 9:15 PM | Finalist presentations & judging |
| 9:45 PM | Awards ceremony |
| 10:00 PM | Event wrap-up & doors close |

## Setup

> **You do not need to bring API keys or accounts.** We provide a dedicated
> **Cognee Cloud** instance (URL + API key) *and* an LLM API key (OpenAI) per
> team at kickoff. No local Docker infra required. Everything below is so you
> know how to wire what we hand you into your project — not a list of things
> to sign up for in advance.

### Prerequisites

- Python 3.10 – 3.14
- A Cognee Cloud instance URL + API key — **provided by us at kickoff**
- An LLM API key — **provided by us at kickoff** (you can also bring your own
  from any [supported provider](https://docs.cognee.ai/setup-configuration/llm-providers))

### 1. Install Cognee

```bash
uv venv && source .venv/bin/activate
uv pip install cognee==1.2.0.dev1
```

> Use the **`1.2.0.dev1`** prerelease for this hackathon — it's the version the
> Cognee Cloud APIs (`cognee.serve` / `remember` / `recall`) are built against.

### 2. Configure the LLM

We hand out an `LLM_API_KEY` at kickoff — export it in your shell:

```bash
export LLM_API_KEY="<key-we-give-you-at-the-event>"
```

Or drop it into a local `.env` based on cognee's [`.env.template`](https://github.com/topoteretes/cognee/blob/main/.env.template).
Prefer your own provider? Set `LLM_PROVIDER` / `LLM_MODEL` per the
[provider docs](https://docs.cognee.ai/setup-configuration/llm-providers).

### 3. Connect to Cognee Cloud (optional, rewarded)

Cognee runs locally by default, so this step is optional — but it's the
highest-leverage thing you can do for your score (see the bonus above). Point
at the **Cognee Cloud** instance we hand you once with `cognee.serve(...)` —
every `remember` / `recall` / `forget` / `improve` call after that targets your
managed instance, with both session memory and the permanent graph inside it:

```python
import cognee

await cognee.serve(
    url="https://your-instance.cognee.ai",   # given at kickoff
    api_key="ck_...",                          # given at kickoff
)
```

### 4. Run the Pipeline

Cognee's API exposes four operations — `remember`, `recall`, `forget`, and
`improve`:

```python
import asyncio
import cognee


async def main():
    # Optional: connect to your managed Cognee Cloud instance (boosts your reward).
    # Drop this line to run fully locally instead.
    await cognee.serve(url="https://your-instance.cognee.ai", api_key="ck_...")

    # Store permanently in the knowledge graph (runs add + cognify + improve)
    await cognee.remember("Cognee turns documents into AI memory.")

    # Store in session memory (fast tier inside the Cloud instance)
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

### 5. Push a local brain to Cognee Cloud

Prefer to build locally first? Develop against a local cognee instance, then
**push** your finished brain up to the Cognee Cloud instance we gave you — an
easy way to earn the Cognee Cloud bonus without changing how you build.

`cognee.push(...)` composes *export + upload*: it exports the dataset as a
portable COGX archive, uploads it to your Cloud instance, and imports it there.
With the default `mode="preserve"` your locally-built graph lands in the Cloud
as-is, with **zero LLM calls on the remote side** (so it's fast and cheap).

```python
import cognee

# Authenticate against your Cloud instance once (credentials handed out at kickoff).
# Auth is reused from the serve stack: live connection -> ~/.cognee/cloud_credentials.json
# -> env vars. Run `cognee-cli serve` once and you can push any time after.
await cognee.serve(url="https://your-instance.cognee.ai", api_key="ck_...")

# Push a local dataset up to the Cloud (remote dataset defaults to the same name).
await cognee.push("company-brain")

# Rename the remote dataset and upload without blocking.
await cognee.push(
    "company-brain",
    target_dataset="prod",
    run_in_background=True,   # poll result.pipeline_run_id for status
)
```

`mode` controls how the remote side treats the upload:

- **`preserve`** (default) — import your locally-extracted graph as-is, no
  remote LLM calls.
- **`hybrid`** / **`re-derive`** — let the remote side enrich or rebuild the
  graph from the imported data instead of taking it verbatim.

`cognee.export(...)` is the building block `push()` reuses. It writes a portable
archive (`cogx` / `json` / `graphml` / `cypher` / `pydantic`) to **local disk**
without touching the Cloud — handy for backups or inspecting what would upload:

```python
await cognee.export("company-brain", format="cogx")  # -> portable file on disk
```

CLI equivalent of the push flow:

```bash
cognee-cli serve              # authenticate against your Cloud instance once
cognee-cli push company-brain # export + upload + import
```

> **Version note:** `push` / `export` require a recent cognee build. If
> `cognee.push` isn't available in your environment, grab the latest cognee at
> kickoff — we'll make sure the event build has it.

### CLI

The same operations are exposed as a CLI:

```bash
cognee-cli remember "Cognee turns documents into AI memory."
cognee-cli recall "What does Cognee do?"
cognee-cli forget --all
```

Launch the local UI with `cognee-cli -ui` (web app at http://localhost:3000).

### Run cognee as a local server

You don't have to use the Cloud to get a server. Cognee can run as a **local
server** on your own machine — the same `remember` / `recall` / `forget` /
`improve` API plus a graph explorer UI, all hosted locally:

```bash
uv pip install cognee==1.2.0.dev1   # if you haven't already
cognee-cli -ui            # starts the local cognee server + web UI at http://localhost:3000
```

Cognee Cloud is the managed version of exactly this server — so you can develop
against the local server during the event and, when you want the reward bonus,
connect with `cognee.serve(...)` or `cognee.push(...)` (below) to move your
brain into the Cloud.

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
2. search(AGENTIC_COMPLETION,          │ Cognee Cloud  │
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
  qa-answerer/
    SKILL.md
```

`my_skills/qa-answerer/SKILL.md`:

```markdown
---
description: Answer questions from the Company Brain, citing sources, and improve from feedback.
allowed-tools: memory_search
---

# Instructions

Answer the question using only what the Company Brain returns. Cite the
sources you used. If the brain has no answer, say so plainly instead of
guessing.
```

A starter version is at
[`my_skills/qa-answerer/SKILL.md`](./my_skills/qa-answerer/SKILL.md) — copy
it, fork it, or replace it with your own. Real Company Brains will usually
have several skills (an ingestor, an answerer, a linter, a critic).

### Run the loop from Python

> **Install first:** `uv pip install cognee==1.2.0.dev1` (see [Setup](#setup)). The imports
> below ship with cognee — no extra packages needed.

```python
import asyncio
import os

import cognee
from cognee import SearchType
from cognee.memory import SkillRunEntry
from cognee.modules.engine.operations.setup import setup

DATASET = "company-brain"
SESSION = "brain-session-1"
SKILLS_DIR = "./my_skills"  # run this from inside the event folder


async def build_locally():
    """Ingest skills, run the agent, score it, then propose + apply an improvement."""
    # Fresh slate — drop these two prune calls if you want to keep prior runs.
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()

    # 1. Ingest skills into the graph, then read the skill names back off the result.
    remembered = await cognee.remember(
        SKILLS_DIR,
        dataset_name=DATASET,
        content_type="skills",
    )
    skill_names = [item["name"] for item in remembered.items if item["kind"] == "skill"]
    if not skill_names:
        raise RuntimeError("No skills were ingested.")

    user, datasets = await resolve_authorized_user_datasets(DATASET, None)
    dataset = datasets[0]

    # 2. Run the agent against the skills. session_id keeps working memory in the
    #    session tier. Ask the agent to return a JSON score.
    answer = await cognee.search(
        "Answer: how is retention calculated? Return JSON with a score 0..1.",
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=[DATASET],
        skills=skill_names,
        max_iter=6,
        session_id=SESSION,
    )
    print("answer:", answer)

    # 3. Score the run. In real life: parse `answer`, run an eval, etc.
    score = 0.3
    skill_to_improve = skill_names[0]

    # 4. Record feedback. apply=False -> propose a rewrite, don't change the
    #    skill yet. score_threshold sets when a proposal is generated.
    proposal_result = await cognee.remember(
        SkillRunEntry(
            selected_skill_id=skill_to_improve,
            task_text="Answer how retention is calculated",
            result_summary="Answer cited no sources and missed a caveat.",
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
    print("proposal_result:", proposal_result)
    proposal_items = result_items(proposal_result)
    print("proposal items:", proposal_items)

    # 5. Apply the proposal explicitly (skip gracefully if none was generated).
    proposal_id = next(
        (
            item["proposal_id"]
            for item in proposal_result.items
            if item.get("kind") == "skill_improvement_proposal"
        ),
        None,
    )
    if proposal_id is None:
        print("No proposal generated — nothing to apply.")
        return

    await improve_skill(
        skill_to_improve,
        dataset=dataset,
        user=user,
        proposal_id=proposal_id,
        apply=True,
    )
    print("proposal_id:", proposal_id)


async def push_to_cloud():
    """Optional, rewarded: push your locally-built brain up to Cognee Cloud.

    Credentials come from the environment — never hardcode your API key.
    Both are handed out at kickoff:
        export COGNEE_CLOUD_URL="https://your-instance.cognee.ai"
        export COGNEE_API_KEY="ck_..."
    """
    await cognee.serve(
        url=os.environ["COGNEE_CLOUD_URL"],
        api_key=os.environ["COGNEE_API_KEY"],
    )
    print("pushed:", await cognee.push(DATASET))


async def main():
    await build_locally()
    # Uncomment once COGNEE_CLOUD_URL / COGNEE_API_KEY are set to earn the bonus:
    # await push_to_cloud()


asyncio.run(main())
```

What the knobs do:

- **`session_id`** — keeps working memory for this run in the session tier
  (inside your Cloud instance when connected, local otherwise). Different
  sessions stay isolated; distillation into the permanent graph happens when
  you call `cognee.remember(...)` without a `session_id` (or via the background
  sync).
- **`max_iter`** — caps how many agent reasoning steps run before returning.
- **`score_threshold`** (in `skill_improvement`) — only generate a proposal
  when the run score falls *below* this value. Raise it to be aggressive
  about improvement; lower it to only react to clear failures.
- **`apply=False`** — propose without rewriting. This example stops after
  returning the `proposal_id`; explicit apply is still a separate follow-up.

Current local/backend caveats:

- **Served `remember()` result shape** — when testing against the local
  backend via `cognee.serve(url="http://127.0.0.1:8000")`, `remember()` may
  currently come back as a plain `dict` instead of a `RememberResult`
  instance. If you need `items`, read them defensively from either
  `result["items"]` or `result.items`.
- **Served skill names** — the current served upload/materialization path may
  canonicalize uploaded skills to names like `skill-0000` instead of
  preserving the source directory name such as `qa-answerer`. When testing
  against the local backend, prefer reading the ingested skill name from
  `remembered.items` and using that value for `search(...)` and
  `SkillRunEntry(...)`.
- **Served search/apply flow** — remote search currently expects
  `datasets=[DATASET]` rather than a bare string, and the explicit
  `improve_skill(..., apply=True)` step is still a separate follow-up after
  proposal generation. A minimal served-mode smoke test can stop after
  printing the returned `proposal_id`.

A full multi-skill version of this loop (three cooperating skills, JSON
parsing, before/after skill bodies) lives in the cognee repo at
[`examples/demos/skill_feedback_loop/skill_feedback_loop_demo.py`](https://github.com/topoteretes/cognee/tree/main/examples/demos/skill_feedback_loop).

## Other Ways to Run Cognee

| What | How | When to use |
|------|-----|-------------|
| Cognee Cloud | `await cognee.serve(url=..., api_key=...)` | **Optional, rewarded** — managed home for your brain; boosts your score |
| Push to Cloud | `await cognee.push("dataset")` | Upload a locally-built brain to your Cloud instance |
| Python SDK | `import cognee` | Building your brain / agent logic (runs locally by default) |
| CLI | `cognee-cli remember / recall / forget` | Smoke-tests, ad-hoc ingestion |
| Local server + UI | `cognee-cli -ui` → http://localhost:3000 | Run cognee as a local server; inspect the graph visually |
| Claude Code plugin | [`cognee-integrations`](https://github.com/topoteretes/cognee-integrations/tree/main/integrations/claude-code) | Giving Claude Code persistent memory |
| Examples | [`examples/`](https://github.com/topoteretes/cognee/tree/main/examples) in the cognee repo | Reference pipelines & demos |

## Submission

Each team submits:

- a short writeup of the idea and self-improvement loop
- the Company Brain implementation (code + skills, if any)
- before/after evidence that the brain improved from feedback
- if you used Cognee Cloud (`cognee.serve` / `cognee.push`), note it — it
  counts toward the **"Best use of Cognee Cloud"** bonus
- a 3-minute demo

Use [`templates/SUBMISSION.md`](./templates/SUBMISSION.md) — copy it into your
team folder or PR description and fill it in.

## Resources

- [Cognee Documentation](https://docs.cognee.ai/)
- [Karpathy on LLM Wikis](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [Discord](https://discord.gg/NQPKmU5CCg)

---

*Full challenge brief, starter skills, and submission template will land in
this folder ahead of the event.*
