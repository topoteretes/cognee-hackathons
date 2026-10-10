> **Code-Repo:** https://github.com/luca-schweigmann/cognee-company-brain
> **Team:** Helios Brain (Luca Schweigmann)

# Hackathon Submission — Company Brain mit Immunsystem

## Team

| Field         | Value                          |
|---------------|-------------------------------|
| Team Name     | Helios Brain                  |
| Company       | Helios (fictional)            |
| Members       | TODO (names of team members)  |
| Contact Email | TODO                          |

---

## Project Overview

**Project Name:** Company Brain — mit Immunsystem

**One-Liner:** A self-auditing company knowledge base built on Cognee that detects contradictions, resolves conflicts with confidence-weighted provenance, and improves its own audit skills autonomously.

**Problem:** Company knowledge is scattered and contradictory. When Alice says the backend lead is Maya and Bob's onboarding doc says it's Thomas, the knowledge base silently holds both — and hallucinating systems answer with whichever fact is retrieved first. There is no mechanism to detect the contradiction, let alone resolve it.

**Solution:** Company Brain ingests structured facts about a fictional company (Helios), continuously audits the graph for contradictions via an adversarial Cognee skill (`conflict_auditor`), resolves conflicts using source-trust and age-weighted confidence scoring, and rolls back unsafe resolutions. The system then logs skill failures, generates targeted feedback, and rewrites the skill itself — improving its own audit logic without human intervention.

**Core Cognee Features Used:**
- `cognee.remember()` — ingesting facts and skills into the graph
- `cognee.recall()` — answering questions with graph context
- `cognee.search(AGENTIC_COMPLETION, skills=[...])` — skill-driven adversarial audit
- Two-tier session isolation: `session_id` for ephemeral audit state vs. permanent graph tier
- Cognee Cloud: `cognee.serve()` + `cognee.push()` for cloud deployment

---

## Three Core Operations

### Operation 1: Ingest

**Entry point:** `brain/ingest.py`

```python
ingest_facts(facts, session_only=False)
# Iterates over Fact objects; calls cognee.remember(fact.to_text()) for each.
# If session_only=True, passes session_id to keep facts in the ephemeral tier.

ingest_skills(skills_dir)
# Calls cognee.remember(skills_dir, content_type="skills")
# Loads conflict_auditor and qa-answerer into the graph's skill registry.
```

The seed dataset (`seed/seed_data.py` → `load_seed()`) contains 59 facts from 4 sources (slack, notion, ticket, meeting) and 5 deliberate conflict clusters, covering attributes like `backend_lead`, `office_location`, `headcount`, `funding_stage`, and `cto`.

---

### Operation 2: Query + Self-Improve

**Entry point:** `brain/query.py`

```python
answer(question, store, session_id)
# 1. Calls cognee.recall(question) to retrieve graph-grounded context.
# 2. Calls score_answer(store.active_facts(key)) to compute confidence.
# 3. Returns answer, confidence, winner, and source lineage.
```

**Confidence formula:**

```
weight(fact) = source_trust * 0.5 ^ (age_days / 180)
confidence   = weight(winner) / sum(all weights for that key)
```

`source_trust` is assigned per source tier: HR system = 1.0, team wiki = 0.8, Slack message = 0.5, unverified = 0.3.

**Self-improvement** is triggered when a skill run logs a low `success_score`. The `SkillRunEntry` records `error_type`, `feedback`, and the score. The loop lives in `brain/demo.py` as `improve_auditor_skill`: it calls `cognee.remember(SkillRunEntry(...), skill_improvement={..., "apply": False})` to propose the patch, then `cognee.improve_skill(apply=True)` to commit it, and finally re-ingests the updated skill via `ingest_skills`.

---

### Operation 3: Lint (Audit + Resolve)

**Entry point (audit):** `brain/audit.py`

```python
run_audit(store, skills, session_id)
# Calls cognee.search(AGENTIC_COMPLETION, skills=['conflict_auditor'])
# with session_id to isolate audit findings.
# Returns a list of ConflictCluster objects.
```

**Entry point (resolve + rollback gate):** `brain/resolve.py`

```python
lint(store, clusters)
# For each ConflictCluster:
#   1. resolve_cluster() — picks winner by confidence; writes to store.
#   2. Re-audits to verify resolution.
#   3. Rollback gate: if confidence < 0.85, reverts via store.snapshot/rollback.
```

---

## Self-Improvement Evidence

This is the central demonstration of the project: the system improves its own audit skill from version 1 to version 2 without human intervention.

### Skill: `my_skills/conflict_auditor/SKILL.md`

### Version 1 Behavior

Audit run finds 4 of 5 conflict clusters. The fifth cluster is missed because two individually consistent entities — `frontend-lead.person = "David Park"` and `lead-frontend-engineer.person = "Sarah Kim"` — look like different attributes to v1. The skill does not know that `frontend-lead` and `lead-frontend-engineer` are aliases for the same role, so it never registers a conflict between them. Only when the alias bridge is applied does v1's blind spot become visible.

| Metric        | Value                                               |
|---------------|-----------------------------------------------------|
| `success_score` | 0.72                                              |
| `error_type`  | `alias_detection_miss`                              |
| `feedback`    | Skill missed ConflictCluster for frontend-lead/lead-frontend-engineer alias pair (David Park vs Sarah Kim). Two individually consistent entities that only contradict via the alias bridge. Add alias normalization rule. |
| Clusters found | 4 / 5                                             |

### After `improve_skill`

The `improve_skill` function reads the `SkillRunEntry`, constructs a targeted patch, and appends an alias normalization rule to `SKILL.md`. The updated skill is re-ingested. On the next audit run, all 5 clusters are found.

| Metric          | Before (v1) | After (v2) |
|-----------------|-------------|------------|
| `success_score` | 0.72        | 1.0        |
| Clusters found  | 4 / 5       | 5 / 5      |

### Before / After: SKILL.md

**Before (v1):**

```markdown
# Conflict Auditor v1
Search for facts where entity.attribute has multiple distinct values.
```

**After (v2 — patch written by `improve_skill` on 2026-06-19):**

```markdown
# Conflict Auditor v2
Search for facts where entity.attribute has multiple distinct values.

## Alias Rule (added by improve_skill 2026-06-19)
Before comparing attribute keys, normalize role aliases:
- "frontend-lead" == "lead-frontend-engineer" == "frontend engineering lead"
Treat aliased keys as the same attribute. Flag as conflict if normalized values differ.
```

---

## Demo Numbers

**Query: "Wer ist der Backend-Lead?"**

| Stage              | Confidence | Winner | Contradictory Facts |
|--------------------|------------|--------|---------------------|
| Before audit       | 0.42       | —      | 3                   |
| After audit + lint | 0.91       | Maya   | resolved, lineage visible |

**Knowledge Health Score:**

| Stage                    | Health Score |
|--------------------------|--------------|
| Before audit             | 0.83         |
| After improve_skill (v2) | 0.96         |

**Lint result (v2 run):** 5 auto-resolved, 6 facts superseded, 5 distilled, 0 flagged, no rollback triggered.

**Conflict clusters found:**

| Audit Run       | Found |
|-----------------|-------|
| v1 skill        | 4 / 5 |
| v2 skill        | 5 / 5 |

---

## Architecture

### Two-Tier Distillation

```
Session Tier (session_id="brain-session-1")       Graph Tier (no session_id)
─────────────────────────────────────────       ──────────────────────────────────
 Adversarial audit findings                      Ingested company facts
 ConflictCluster detection results               Distilled (resolved) facts
 SkillRunEntry logs                              Skills (conflict_auditor, qa-answerer)
 Temporary hypotheses                            Permanent knowledge

  [cognee.remember(..., session_id=SESSION)]       [cognee.remember(...)]
                   |                                        |
                   +──── distill: resolve_cluster ──────────+
                             (only if confidence >= 0.85)
```

Ephemeral audit results stay in the session tier until a resolution passes the rollback gate. Only then does the winner fact get distilled into the permanent graph tier. This prevents noisy or low-confidence conclusions from polluting the knowledge base.

### Was Cognee macht / was der Store macht

**Cognee** owns the knowledge layer: `cognee.remember()` ingests facts and skills into the graph, `cognee.recall()` retrieves graph-grounded context, `cognee.search(AGENTIC_COMPLETION, skills=[...])` drives the adversarial audit, `SkillRunEntry` + `cognee.improve_skill(apply=True)` run the self-improvement loop, and `cognee.serve()` / `cognee.push()` handle cloud deployment. Session isolation (`session_id` vs. no session_id) is a native Cognee primitive — ephemeral audit state stays in the session tier; distilled winners go to the permanent graph tier.

**The deterministic Store** (`brain/provenance.py`) owns auditability: lineage tracking (`parent_ids`), explainable confidence scoring (source-trust × time-decay formula), the resolution gates, and snapshot/rollback. This is what makes our numbers auditable rather than a black box — every resolved fact can be traced back to its originals, which are never deleted.

**Rollback semantics:** rollback is a provenance-layer rollback — `Store.rollback(snapshot_id)` reverts the Store's in-memory state to the snapshot taken before the lint pass. Originals in the Cognee graph are never deleted, so the graph itself is always recoverable. Layers 4–5 (Diversity Guard, No-Echo Guard) are documented guard stubs that explain the design intent; they are not active enforcement in this submission. This separation of concerns — Cognee for knowledge, Store for auditability — is deliberate, not a limitation.

### File Layout

```
cognee-company-brain/
├── brain/
│   ├── config.py        # boot(), push_to_cloud()
│   ├── models.py        # Fact, ConflictCluster
│   ├── ingest.py        # Operation 1: ingest_facts(), ingest_skills()
│   ├── query.py         # Operation 2: answer(), score_answer(), weight()
│   ├── audit.py         # Operation 3a: run_audit()
│   ├── resolve.py       # Operation 3b: lint(), resolve_cluster()
│   ├── provenance.py    # Store: snapshot, rollback, health()
│   └── demo.py          # Demo runner: main(), improve_auditor_skill()
├── my_skills/
│   ├── conflict_auditor/SKILL.md
│   └── qa-answerer/SKILL.md
├── seed/
│   └── seed_data.py     # load_seed() — 59 facts, 5 conflict clusters
├── docs/
│   ├── CONTRACT.md      # Interface contract
│   ├── PLAN.md          # Implementation plan
│   └── plan.html        # Visual plan
├── .env.template
├── Makefile
└── SUBMISSION.md
```

---

## Cognee Cloud

**Configuration:** `brain/config.py`

```python
boot(use_cloud=True)
# Calls cognee.serve(url=COGNEE_CLOUD_URL, api_key=COGNEE_API_KEY)

push_to_cloud(dataset)
# Calls cognee.push(dataset)
```

**CLI:**

```bash
python -m brain.demo --push
```

**Makefile:**

```bash
make push   # runs demo + cloud push
```

**Cloud Instance URL:** TODO (Cognee Cloud instance URL after deployment)

---

## Agents and Skills

| Skill              | File                                    | Purpose                                                         |
|--------------------|-----------------------------------------|-----------------------------------------------------------------|
| `conflict_auditor` | `my_skills/conflict_auditor/SKILL.md`   | Adversarial self-querier; detects contradictory facts in graph. Improved live from v1 to v2. |
| `qa-answerer`      | `my_skills/qa-answerer/SKILL.md`        | Answers questions with source citations and confidence score.   |

Both skills are invoked via:

```python
cognee.search(AGENTIC_COMPLETION, skills=['conflict_auditor', 'qa-answerer'])
```

---

## Reproduction

```bash
make setup
# pip install cognee==1.2.0.dev1
# cp .env.template .env
# Fill .env with LLM_API_KEY, COGNEE_API_KEY, and optionally COGNEE_CLOUD_URL

make spike
# python -m brain.spike — end-to-end API verification (smoke test)

make demo
# python -m brain.demo — full 3-minute demo run

make push
# python -m brain.demo --push — demo + cloud push
```

**Required environment variables (`.env.template` → copy to `.env`):**

```
LLM_API_KEY=<your LLM provider key>
COGNEE_API_KEY=<your Cognee key>
COGNEE_CLOUD_URL=<optional, for cloud push>
```

---

## Demo Outline (6 Beats, ~3 minutes)

| Time     | Beat | Action                                                                                   |
|----------|------|------------------------------------------------------------------------------------------|
| 0:00–0:20 | 1   | **Ingest** — `load_seed()` ingests 59 facts + 5 conflict clusters; skills loaded.       |
| 0:20–0:50 | 2   | **Naive query** — Ask "Wer ist der Backend-Lead?"; system returns confidence 0.42 and 3 contradictory facts with no clear winner. |
| 0:50–1:20 | 3   | **Audit v1** — `run_audit()` with `conflict_auditor` v1 finds 4/5 clusters; `success_score` 0.72; `alias_detection_miss` logged. |
| 1:20–1:50 | 4   | **Self-improvement** — `improve_skill()` patches SKILL.md with alias normalization rule; v2 re-ingested; re-audit finds 5/5 clusters; `success_score` 1.0. |
| 1:50–2:20 | 5   | **Lint + rollback gate** — `lint()` resolves all clusters; winner Maya passes gate (confidence 0.91); 5 auto-resolved, 6 superseded, 5 distilled, 0 flagged; no rollback triggered; health score rises from 0.83 to 0.96. |
| 2:20–3:00 | 6   | **Verified query** — Same question returns confidence 0.91, winner Maya, full source lineage visible. Cloud push if `--push` flag set. |

---

## Links

| Resource             | URL                                                |
|----------------------|----------------------------------------------------|
| Repository (GitHub)  | TODO                                               |
| Live demo video      | TODO                                               |
| Cognee Cloud instance | TODO                                              |
