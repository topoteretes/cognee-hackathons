# Team Submission

## Team

- Team name: Banking memory
- Participants: Mohnish SaI Prsad, Alejo Lovallo.
- Wiki / project name: Banking memory

## Wiki Overview

Banking Memory is a self-improving financial knowledge wiki that ingests banking data from Plaid API, stores it in a Cognee knowledge graph with Redis vector embeddings, and automatically detects and fills knowledge gaps during queries. When a user asks a question, the system performs semantic search across stored financial data, analyzes the completeness of the answer using GPT-4o-mini as a "gap detector," and autonomously remembers missing facts to improve future responses—creating a continuously enriching knowledge base that gets smarter with every query.

- **Domain or data sources**: Banking and financial data via Plaid API (accounts, transactions, balances, identity, auth data)
- **Primary use case**: AI assistants and agents querying financial information with automatic context enrichment and self-improvement
- **What makes it stand out**: Autonomous knowledge gap detection and self-healing loop—the wiki critiques its own answers, identifies missing information, and automatically ingests improvements without human intervention. Combines Redis vector search for fast semantic retrieval with Cognee's permanent knowledge graph for durable, cross-session learning.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...):
- How it is captured (`cognee.remember(...)`, custom pipeline, ...):
- Code entry point:

### Query + Self-improve

- How users query the wiki:
- Where feedback comes from (user rating, agent critic, eval, ...):
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting,
  graph rewrite, ...):
- Code entry point:

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale
  pruning, ...):
- How it runs (scheduled, on-write, on-demand):
- Code entry point:

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

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
- What changed in the wiki between runs:

```text
Before:

After:
```

## Architecture

Short diagram or bullet list of components. The hackathon's core pattern is
**Redis as session memory, distilled into Cognee's permanent knowledge graph**
— show how your wiki uses that split.

![Arch](./Diagram.png)

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...):
- How and when content is distilled into the graph:
- What stays in Redis vs. what gets promoted:
- How distillation quality improved between baseline and improved run:

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
LLM_API_KEY
REDIS_URL
# add anything else your wiki needs
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

- Repo: https://github.com/AlejoLovallo/cognee-hackathon-plaid
- Slides / writeup: ![slides](./Banking-memory.pdf)
