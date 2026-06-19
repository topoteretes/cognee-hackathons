# Team Submission

## Team

- Team name:
- Participants:
- Company Brain / project name:

## Company Brain Overview

One-paragraph description of what your Company Brain does and how it self-improves.

- Domain or data sources:
- Primary use case:
- What makes it stand out:

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...):
- How it is captured (`cognee.remember(...)`, custom pipeline, ...):
- Code entry point:

### Query + Self-improve

- How users query the Company Brain:
- Where feedback comes from (user rating, agent critic, eval, ...):
- How feedback updates the brain (`SkillRunEntry`, edge re-weighting,
  graph rewrite, ...):
- Code entry point:

### Lint

- What "linting" means in your brain (dedupe, conflict resolution, stale
  pruning, ...):
- How it runs (scheduled, on-write, on-demand):
- Code entry point:

## Self-Improvement Evidence

Show that the brain actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task:
- Result:
- Score (your own metric, judge-readable):
- Recorded feedback:

```text
error_type:
error_message:
feedback:
success_score:
```

### Improved Run

- Query / task:
- Result:
- Score:
- What changed in the brain between runs:

```text
Before:

After:
```

## Architecture

Short diagram or bullet list of components. The hackathon's core pattern is
**Cognee Cloud as the single home for both tiers** — session memory
(`session_id=...`) is the fast per-conversation scratchpad inside the Cloud
instance, and the permanent graph (no `session_id`) is the durable,
cross-session knowledge that session content is distilled into. Show how your
brain uses that split.

```text
[ingest / agent turns]
        |
        v
[ Cognee Cloud — session memory ]   <- hot, per-conversation (session_id=...)
        |
        | distillation (what gets promoted? how?) — inside the Cloud instance
        v
[ Cognee Cloud — permanent graph ]  <- durable, cross-session (no session_id)
        |
        v
[ recall / agent loop ]
        |
        v
[ feedback -> improve ]
```

### Cognee Cloud (optional, rewarded)

Did you connect your Company Brain to Cognee Cloud (`cognee.serve(...)` or
`cognee.push(...)`)? It's optional, but it counts toward the **"Best use of
Cognee Cloud"** bonus. If you did, both tiers live inside that managed instance
— describe how you used it below. If you stayed local, leave this section blank.

- What the team writes to session memory (`session_id=...`) — raw turns,
  intermediate observations, per-conversation scratchpad:
- What goes straight to the permanent graph (no `session_id`) — durable,
  cross-session facts:
- How and when content is distilled from session memory into the permanent
  graph, inside the Cloud instance (what gets promoted? what triggers it?):
- What stays session-only vs. what gets promoted:
- Proof the brain got smarter between baseline and improved run (how
  distillation quality improved):

## Agents / Skills (if any)

If you used skill packs or multi-agent roles:

```text
Skill path(s):
Roles:
  - Ingestor:
  - Querier:
  - Linter:
  - Critic:
```

## Reproduction

Commands to reproduce your demo:

```bash
# paste commands here
```

Environment variables required:

```text
COGNEE_CLOUD_URL    # your dedicated Cognee Cloud instance URL (https://your-instance.cognee.ai)
COGNEE_API_KEY      # your Cognee Cloud API key (ck_...)
LLM_API_KEY
# add anything else your brain needs
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions:
- 3-minute pitch outline:

```text
1. Problem / idea
2. Ingest demo
3. Query demo (before improvement)
4. Self-improve step
5. Query demo (after improvement)
6. What is next
```

## Links

- Repo:
- Slides / writeup:
- Anything else:
