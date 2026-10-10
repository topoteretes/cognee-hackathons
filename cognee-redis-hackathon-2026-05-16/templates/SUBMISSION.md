# Team Submission

## Team

- **Team name:** flywheel
- **Participants:** Beibei (Sylvia) Wang
- **Wiki / project name:** **PaperGraph** — a self-improving literature wiki for AI/ML researchers

---

## Wiki Overview

PaperGraph turns the messy pile of papers a researcher accumulates into a queryable
knowledge graph that gets sharper every time it's used. You drop in a paper + a takeaway
note; PaperGraph extracts entities (paper, author, concept, method, dataset) and links
them to what you've read before. When you ask a research question, it answers from the
graph and cites the underlying papers. When the answer is wrong or incomplete, you
record one line of feedback — and the next time you ask a similar question, the answer
improves because the graph has been re-weighted, augmented, or rewritten in response.

- **Domain / data sources:** AI/ML research papers (arXiv PDFs + user-written takeaway notes), focused on RL post-training, agentic RL, and LLM alignment for the demo.
- **Primary use case:** Independent researchers, PhD students, and small labs who read 10+ papers/week and forget 80% of them within 3 months.
- **What makes it stand out:** Existing tools (Zotero, Notion, Obsidian) are static buckets. PaperGraph is the first paper tool that **gets smarter with use** — every query/feedback loop tightens the graph.

---

## The Three Operations

### Ingest

- **What goes in:** A paper (arXiv link or PDF) + a short takeaway note from the reader (2–10 sentences). Optionally, highlights and questions captured while reading.
- **How it is captured:**
  - **During reading** → `paper_wiki.read_session(paper_id, note)` writes raw notes / highlights / questions into Redis under `session_id = f"reading:{paper_id}"`. Cheap, immediate, no LLM cost.
  - **On "done reading" trigger** → `paper_wiki.promote_session(paper_id)` runs the cognify pipeline that distills the session into the permanent graph: paper node, concept nodes, edges to previously ingested papers (cites / builds-on / contradicts / applies-to).
- **Code entry point:** `paper_wiki.py::ingest_paper`, `paper_wiki.py::promote_session`

### Query + Self-improve

- **How users query the wiki:** `paper_wiki.query(question, session_id)` — natural-language question against the graph. Uses cognee's `recall` with `GRAPH_COMPLETION` mode so answers come from graph traversal, not just vector similarity. Each answer cites the underlying paper nodes.
- **Where feedback comes from:** The reader rates each answer (1–5) and writes a one-line critique ("missed process reward models", "didn't connect GRPO to variance reduction theory"). Captured via `paper_wiki.record_feedback(qa_id, score, text)`.
- **How feedback updates the wiki:**
  - Score < 3 with a critique → critique is itself ingested as a takeaway note attached to the queried concepts. Next cognify pass adds missing edges.
  - Repeated low-score answers around a concept → that concept is flagged in `lint` for explicit review.
  - Score ≥ 4 → the (question, answer, cited-papers) triple is stored as a positive exemplar that boosts ranking for similar future queries.
- **Code entry point:** `paper_wiki.py::query`, `paper_wiki.py::record_feedback`

### Lint

- **What "linting" means here:**
  - **Dedupe:** Same paper across arXiv v1/v2/v3 → merge into one canonical node.
  - **Conflict resolution:** Same concept described differently across two notes → flag for reconciliation.
  - **Stale pruning:** Takeaways untouched for 6+ months AND not cited by any newer note → marked `stale` (not deleted — the researcher decides).
  - **Orphan check:** Concept nodes referenced by exactly one paper → candidates for merging into a parent concept.
- **How it runs:** On-demand (CLI: `python -m paper_wiki lint`). For hackathon demo, also runs once between baseline and improved runs.
- **Code entry point:** `paper_wiki.py::lint_wiki`

---

## Self-Improvement Evidence

### Baseline Run

- **Query / task:**
  > "I'm designing reward shaping for an agentic RL task with sparse rewards. What approaches should I consider and what are the trade-offs?"
- **Papers in wiki at baseline (3):**
  - Schulman et al., *Proximal Policy Optimization Algorithms* (2017)
  - Shao et al., *DeepSeekMath* (GRPO, 2024)
  - DeepSeek-AI, *DeepSeek-R1* (2025)
- **Result:**

  > Consider leveraging GRPO (Group Relative Policy Optimization) for reward shaping in your agentic RL task, as discussed in the paper "DeepSeek-R1: Incentivizing Reasoning via RL". This approach is beneficial for sparse rewards by using group-relative rewards as advantages, which can help capture more nuanced learning signals.
  >
  > **Trade-offs:**
  > 1. **Simplicity vs. Complexity:** GRPO removes the critic component, simplifying implementation and saving memory, but this may result in less robust performance compared to more complex methods.
  > 2. **Performance vs. Readability:** The method can enhance emergent reasoning through pure-RL training but may sacrifice readability in reward structures.
  > 3. **Generalization vs. Specificity:** Utilizing rule-based rewards (e.g., answer correctness and format) may ensure higher alignment with specific goals, but may not generalize well across different tasks.

  _注：只覆盖 GRPO,缺 PRM / reward hacking / scaling law_

- **Expected weakness:** Discusses PPO clipping and GRPO group baseline at a surface level. Does NOT mention process vs outcome reward models, does NOT discuss reward hacking, does NOT connect GRPO's group baseline to variance reduction theory.
- **Score (1–5):** 2/5
- **Recorded feedback:**

```
error_type: incomplete_coverage
error_message: Missed entire process reward model (PRM) literature; no discussion of reward hacking risk; GRPO mentioned but not connected to variance reduction theory
feedback: For sparse-reward agentic RL the most important axis is process vs outcome reward. Add Uesato 2022 and Lightman 2023 (Let's Verify Step by Step). Also reward hacking trade-off — Gao 2023 scaling laws for reward model overoptimization.
success_score: 0.4
```

### Improved Run

Between runs, six papers added + above feedback ingested + one `lint` pass.

- **Papers added (6):**
  - Rafailov et al., *Direct Preference Optimization* (DPO, 2023)
  - Lightman et al., *Let's Verify Step by Step* (PRM, 2023)
  - Uesato et al., *Solving math word problems with process- and outcome-based feedback* (2022)
  - Gao et al., *Scaling Laws for Reward Model Overoptimization* (2023)
  - Ouyang et al., *Training Language Models to Follow Instructions with Human Feedback* (InstructGPT, 2022)
  - Bai et al., *Constitutional AI* (2022)
- **Query / task:** _(same exact query as baseline)_
- **Result:**

  > To design reward shaping for agentic RL tasks with sparse rewards, consider the following approaches:
  >
  > 1. **Process Reward Models (PRMs)**: These models supervise each reasoning step rather than just the final answer, which enhances credit assignment in sparse environments.
  >    - **Trade-off**: Effective for sparse rewards but requires careful design to ensure correct step supervision.
  >
  > 2. **Rule-based Rewards**: Implement rewards based on specific criteria like answer correctness and format without using a learned model, ensuring straightforward evaluation.
  >    - **Trade-off**: Simplifies reward assignment but may lack flexibility in complex tasks where learned behavior is beneficial.
  >
  > 3. **Proxy Rewards**: Use surrogate measures to simplify the reward landscape, which can mitigate the stinginess of sparse rewards.
  >    - **Trade-off**: This can lead to reward hacking, where the learned behavior diverges from the true objective as optimization hardens.
  >
  > 4. **Scaling Laws**: Refer to empirical findings that suggest the importance of balancing optimization intensity with reward model size to avoid divergence from objectives.
  >    - **Trade-off**: While deeper optimizations can yield better general solutions, they may complicate the reward landscape and potentially degrade agent performance.
  >
  > Ultimately, you will need to monitor and evaluate the effects of these approaches, balancing between complexity and effectiveness for your specific RL task.

  _note：cover PRM、reward hacking、scaling law,4 个 trade-off instead of the original 3 ,which is more clear_

- **Expected improvements:** Discusses process reward (citing Lightman 2023, Uesato 2022) vs outcome reward (citing GRPO, DPO) as the primary axis. Discusses reward hacking with explicit reference to Gao 2023. Connects GRPO's group-relative baseline to variance reduction.
- **Score (1–5):** 4.5/5
- **What changed in the wiki between runs:**

```
Before:
  - 3 paper nodes
  - ~12 concept nodes (mostly PPO/GRPO-specific)
  - 0 nodes for: process_reward, outcome_reward, reward_hacking, variance_reduction
  - 0 edges connecting GRPO to broader RLHF literature

After:
  - 9 paper nodes (+6)
  - ~38 concept nodes (+26)
  - New concept nodes: process_reward_model, outcome_reward_model, reward_hacking,
    variance_reduction, group_relative_baseline, sparse_reward
  - New edges: GRPO --uses--> group_relative_baseline --is-instance-of--> variance_reduction
  - New edges: PRM --addresses--> sparse_reward; PRM --contrasts-with--> ORM
  - New edges: reward_hacking --observed-in--> [GRPO, PPO, DPO]
  - 1 feedback note ingested as first-class takeaway, attached to "reward shaping" concept
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Reader (CLI / notebook)                                    │
│   • read paper           • ask query          • give feedback│
└──────────┬──────────────────┬─────────────────┬─────────────┘
           │                  │                 │
           ▼                  ▼                 ▼
┌──────────────────┐  ┌─────────────────┐  ┌────────────────┐
│  Redis           │  │  Cognee         │  │  Feedback      │
│  session memory  │◄─┤  recall first,  │  │  → re-ingest   │
│                  │  │  fallback graph │  │     as note    │
│  per-paper       │  └────────┬────────┘  └────────┬───────┘
│  reading session │           │                    │
│  • raw highlights│           │                    │
│  • open questions│           ▼                    ▼
│  • temp linkages │  ┌─────────────────────────────────────┐
└────────┬─────────┘  │  Cognee permanent graph             │
         │            │  • paper nodes                      │
         │ promote on │  • concept / method / dataset nodes │
         │ "done      │  • cites / builds-on / contradicts  │
         │ reading"   │  • feedback-derived nodes & edges   │
         └──────────► │                                     │
                      └────────────┬────────────────────────┘
                                   │
                                   ▼
                            lint (on-demand)
                       dedupe • conflict • stale
```

### Redis-as-session-memory

- **What the agent writes into Redis:**
  - Raw highlights pulled from the PDF while reading
  - Open questions the reader jots down ("why does this not use a value baseline?")
  - Tentative cross-references ("reminds me of X paper") not yet confirmed
- **How and when content is distilled into the graph:**
  - Explicit trigger: reader runs `promote_session(paper_id)` when done reading.
  - Auto trigger (stretch goal, not required for demo): reading session idle for 24h → auto-promote.
  - Distillation pipeline: cognee's `cognify` extracts entities + relationships from session notes, merges with existing graph, runs `improve` to refine.
- **What stays in Redis vs. promoted:**
  - **Stays:** Open questions the reader didn't resolve. Half-formed linkages. Page-level highlights.
  - **Promoted:** Structured takeaway (the explicit "here is what I learned" note). Paper-to-paper relationships the reader confirmed. Concepts the reader explicitly named.
- **How distillation quality improved between baseline and improved run:**
  - Baseline: cognify extracted entities flatly from each note in isolation.
  - Improved: feedback ("connect GRPO to variance reduction") was itself ingested as a structured edge-hint, biasing the cognify pass on the next ingestion to look for that relationship in newly added papers.

---

## Agents / Skills

```
Skill path(s):  my_skills/code-review/SKILL.md  (reused for note-quality QC, optional)
Roles:
  - Ingestor:  reads paper + note, writes Redis session, triggers promote_session
  - Querier:   runs query() against graph, returns answer + citations
  - Linter:    runs lint_wiki(), surfaces dedupe / conflict / stale items
  - Critic:    the reader themselves (manual feedback) — no LLM critic for v1
```

---

## Reproduction

```bash
# 1. Setup
uv venv && source .venv/bin/activate
uv pip install "cognee[redis]" python-dotenv

# 2. Start Redis (docker is easiest)
docker run -d -p 6379:6379 --name papergraph-redis redis:7

# 3. Configure .env (see below)
cp .env.example .env  # then edit

# 4. Run the demo: baseline → feedback → improved
python demo.py

# 5. Optional: run lint between baseline and improved
python -m paper_wiki lint
```

### Environment variables required

```bash
# LLM
LLM_API_KEY=sk-...
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Redis (session memory backend)
CACHE_PROVIDER=redis
CACHE_HOST=localhost
CACHE_PORT=6379
```

---

## Demo

- **Live demo link:** _[Loom link — record after final run]_
- **3-minute pitch outline:**

```
1. Problem (30s)
   - "I read 10+ papers a week and forget 80% within 3 months.
      Existing tools are dumb buckets — they don't get smarter with use."

2. Ingest demo (30s)
   - Drop a paper + 3-sentence takeaway → graph auto-extracts paper/concept nodes,
     links to existing literature.

3. Query (before) (30s)
   - Ask: "reward shaping for sparse-reward agentic RL — approaches and trade-offs?"
   - Show: surface-level answer, cites only 2 papers, missing PRM/reward-hacking.

4. Self-improve step (45s)
   - Show feedback line being recorded.
   - Show 6 more papers ingested.
   - Show graph diff: new concept nodes for process_reward, reward_hacking, etc.
   - Show lint output catching one duplicate.

5. Query (after) (30s)
   - Same exact question.
   - Show: nuanced answer with process vs outcome axis, cites 7 papers,
     explicitly discusses reward hacking trade-off.

6. What's next (15s)
   - PDF auto-parsing for highlights, LLM critic to replace manual feedback,
     personal vs lab-shared wiki tier.
```

---

## Links

- **Repo:** github.com/mustardbloom
- **Slides / writeup:** This document
- **Anything else:** Built on cognee 1.0 + Redis 7. The session/graph split is exactly the hackathon's intended pattern — Redis for hot per-reading session, cognee graph for durable cross-session memory.
