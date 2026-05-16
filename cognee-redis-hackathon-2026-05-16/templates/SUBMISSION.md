# Hackathon Submission: Self-Evolving GTM Brain
Github Repo: https://github.com/DDRXV/cognee-hackathon

## Team / Project

**Team name:** SkillAgents AI GTM Brain  
**Project title:** Self-Evolving GTM Brain — A Sales Knowledge Graph That Gets Smarter After Every Deal  
**Track:** Cognee × Redis Knowledge Graph Hackathon 2026  

---

## Wiki Overview

### What domain does your wiki cover?

Enterprise B2B sales intelligence for SkillAgents AI — an enterprise AI training platform. The wiki covers:

- **Product knowledge**: What SkillAgents AI sells, pricing, ROI proof points, differentiation from Coursera/LinkedIn Learning
- **ICP definitions**: Two ideal customer profiles — ICP A (Enterprise, 500–5000 employees) and ICP B (Scaling Tech, 50–500 engineers)
- **Prospect landscape**: 5 target companies with fit scores, tech stacks, buying signals, and qualification status
- **Competitive context**: Positioning against Coursera, LinkedIn Learning, Workday Learning, Degreed
- **Winning signals**: Behavioral and firmographic triggers that indicate deal readiness
- **Deal lessons**: Closed-won patterns and stall reasons, accumulated from every deal outcome

### What is the shape of your knowledge graph?

After full ingestion (Stage 1 + Stage 4 evolution):

| Metric | Value |
|--------|-------|
| Graph nodes | 84+ |
| Graph edges | 228+ |
| Entity types | Company, Person, BuyingSignal, Technology, LessonLearned, ICP, Competitor, DealOutcome |
| FK edge tables (dlt) | signals, tech_stack, contacts, deal_outcomes |

The graph emerges from two sources:
1. **Unstructured text** → `cognee.add()` extracts entities from the SDR playbook and ICP profile docs
2. **Structured dlt resource** → `@dlt.resource` with nested arrays (signals, tech_stack, contacts) where each nested row carries a `company_id` FK — Cognee converts these FK relationships into directed graph edges

---

## Three Operations

### INGEST (`01_ingest.py`)

Mixed ingestion pipeline combining unstructured text and typed structured data:

```python
# Unstructured: SDR playbook + ICP profiles
await cognee.add(sdr_playbook_text, dataset_name="sdr_playbook")
await cognee.add(icp_profiles_text, dataset_name="icp_profiles")
await cognee.cognify()

# Structured: 5 prospect companies via dlt @dlt.resource
@dlt.resource(name="prospects", primary_key="id")
def get_prospects():
    yield [{
        "id": 1, "company_name": "GlobalBank Corp", "icp_fit_score": 10,
        "signals":    [...],   # → Company → BuyingSignal edges
        "tech_stack": [...],   # → Company → Technology edges
        "contacts":   [...],   # → Company → Person edges
    }, ...]

pipeline = dlt.pipeline(pipeline_name="prospects_pipeline", destination="duckdb")
pipeline.run(get_prospects())
```

**Why dlt matters:** The FK mechanism (`company_id` on nested rows) becomes directed graph edges in Cognee. "Which companies share the same LMS vendor?" is answerable by graph traversal, not text similarity.

**Output:** 84+ nodes, 228+ edges across 4 tables. Graph emerges from structure.

---

### QUERY / RETRIEVE (`02_retrieve.py`)

Agentic multi-hop reasoning using `SearchType.GRAPH_COMPLETION`:

```python
results = await cognee.search(
    query_text="Which prospect companies best match our ICP?",
    query_type=SearchType.GRAPH_COMPLETION,
)
```

Three GTM queries demonstrating graph traversal vs. keyword search:

| Query | Graph-traversal insight |
|-------|------------------------|
| ICP Match Ranking | Ranked 5 companies using signals + tech_stack + ICP criteria simultaneously |
| BuildFast SaaS outreach | CTO's LinkedIn post about Cursor AI → AI literacy gap signal → ICP B winning pattern |
| GlobalBank Corp objections | LMS vendor + compliance posture + AI initiative → specific objection-response pairs |

**Why GRAPH_COMPLETION over vector search:** The BuildFast chain (CTO post → tool signal → ICP pattern) requires traversing 3 hops. Pure vector similarity returns similar text; graph traversal returns connected reasoning.

---

### LINT / AUDIT (`03_lint.py`)

Seven-section knowledge wiki audit — the Karpathy LLM.txt equivalent:

```
[PRODUCT KNOWLEDGE]      What does SkillAgents AI sell? Pricing, ROI, differentiators.
[ICP DEFINITIONS]        ICP A (Enterprise) + ICP B (Scaling Tech). Firmographic + behavioral.
[PROSPECT LANDSCAPE]     All 5 companies: fit scores, tech stack, qualification status.
[COMPETITIVE CONTEXT]    Coursera, LinkedIn Learning, Workday, Degreed — positioning gaps.
[BEST FIT TARGETS]       Priority ranking with reasoning. Who to deprioritize and why.
[WINNING SIGNALS]        Buying triggers + deal patterns that indicate readiness.
[GRAPH EDGES — dlt]      LMS vendor overlap, AI tool adoption across prospects (graph-only facts).
```

The seventh section — Graph Edges — demonstrates something pure text audit cannot: relationships that only exist because dlt FK edges became graph edges. "Which companies share Cornerstone as their LMS vendor?" is a graph query, not a document query.

---

## Self-Improvement Evidence

### The Mechanism

Stage 4 closes the feedback loop:

```
Deal closes → Redis HSET (1ms, 24h TTL) → cognee.cognify() (30–90s) → graph updated
                                                                          ↓
                                                         Same query → richer answer
```

Redis gives **instant signal capture** while Cognee's pipeline processes asynchronously. Without Redis, there's a 30–90s blind spot between when a deal closes and when the signal is queryable. With Redis, the outcome is immediately inspectable — then promoted to permanent memory when cognify completes.

### Before Evolution

**Query:** *"What is the best personalized outreach angle for BuildFast SaaS?"*

**Answer:**
> "Noticed BuildFast is on GitHub Copilot + Cursor — we help engineering teams turn tool rollouts into measurable adoption in weeks. 30-day pilot for 50 engineers. 15-minute sync?"

Generic ICP B framing. No ROI quantification. No close-time reference. No proof points.

### After Evolution (same query, same graph, two deal outcomes ingested)

**Answer:**
> "Saw Ben's note that 60% of engineers haven't opened Cursor — your 400 engineers average 4 months to full productivity, that's $240K per hire in ramp cost. SkillAgents cuts that to 6 weeks. Proven: 18-day close with similar Scaling Tech ICP. 14-day pilot to show the lift. Which day this week?"

ROI math anchored to CTO's public statement. $240K ramp cost quantified. 18-day close cited as proof point. Outcome-driven framing.

### What changed in the graph

| Before evolution | After evolution |
|-----------------|-----------------|
| BuildFast node + signals | + `LessonLearned: ROI_quantification_converts_ICP_B_CTOs` |
| Generic ICP B win pattern | + `ClosedWon: 18_day_close_via_ROI_math` |
| No FinServ compliance data | + `LessonLearned: FinServ_requires_SOC2_before_first_call` |
| Redis: 0 deal signals | Redis: 2 signals cached (`skillagents:signal:deal-001`, `deal-002`) |

### Why this is genuine self-improvement

The before/after answers come from the **identical query string** against the same Cognee instance. The only thing that changed is `cognee.cognify(datasets=["deal_outcomes"])` running on the two simulated deal outcomes. The richer answer is not prompt engineering — it is graph traversal returning nodes that didn't exist before the deal closed.

---

## Architecture

### Two-Tier Memory

```
Deal Outcome / Signal
        │
        ▼
Redis (HSET, 24h TTL)          ← Session memory: fast, ephemeral, per-run
  ~1ms write latency              Signals immediately inspectable
  Key: skillagents:signal:deal-001
        │
        │ cognify() pipeline (30–90s)
        ▼
Cognee Knowledge Graph          ← Permanent memory: entities, relationships, lessons
  Ladybug graph + LanceDB         Queryable across sessions forever
  SearchType.GRAPH_COMPLETION
        │
        ▼
SDR Gets Smarter Answer
        │
        └──── next deal closes ────┘  (the self-evolving loop)
```

### Redis as Session Memory

Redis serves as the **real-time signal buffer** between deal events and the knowledge graph:

```python
# Deal closes → Redis HSET immediately (1ms)
r = redis.from_url(REDIS_URL)
r.hset(f"skillagents:signal:{outcome['id']}", mapping={
    "company": outcome["company"],
    "result":  outcome["result"],
    "lesson":  outcome["lesson"],
    "cached_at": datetime.utcnow().isoformat(),
})
r.expire(key, 86400)   # 24h TTL — signal is ephemeral
```

**Why Redis for session memory:**
- **Speed**: HSET is ~1ms. The moment a rep marks a deal won/lost, the signal is captured.
- **Inspectability**: `HGETALL skillagents:signal:deal-001` shows the full signal in < 1ms while Cognee's 30–90s pipeline runs.
- **TTL semantics**: 24h TTL models ephemeral session state — signals are short-lived until distilled into permanent graph nodes.
- **Decoupling**: Redis absorbs deal signals at the rate they arrive; Cognee processes them at its own pace. No blocking.

**Redis is NOT the vector store.** Cognee uses LanceDB (embedded) for vector indexing. Redis is the hot scratchpad — the 30–90s Cognee pipeline is what makes signals semantically queryable.

### Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| Knowledge graph | Cognee 1.1.0 (Ladybug + LanceDB) | Permanent memory, graph traversal |
| Session cache | Redis (Docker) | Real-time signal buffer, 24h TTL |
| Structured ingestion | dlt `@dlt.resource` | FK edges → graph edges |
| LLM + embeddings | OpenAI GPT-4o / text-embedding-3 | Entity extraction, GRAPH_COMPLETION |
| Language | Python 3.10 | — |

---

## Reproducing the Demo

### Prerequisites

```bash
# 1. Start Redis
docker run -d --name redis-cognee -p 6379:6379 redis:latest

# 2. Install dependencies
pip install "cognee[redis]" dlt python-dotenv

# 3. Configure environment
cp .env.example .env
# Add OPENAI_API_KEY to .env
```

Required `.env` variables:

```
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-...
LLM_API_KEY=sk-...                    # same key, cognee reads this name
VECTOR_DB_SUBPROCESS_ENABLED=false    # prevents "too many open files" on macOS
```

### Run

```bash
# Full interactive demo (pauses between stages)
chmod +x demo.sh && ./demo.sh

# Or run stages individually
python 01_ingest.py    # ~60–90s — builds knowledge graph
python 02_retrieve.py  # ~10s  — ICP ranking, outreach, objections
python 03_lint.py      # ~60s  — 7-section knowledge audit
python 04_evolve.py    # ~90s  — self-evolution: before → after

# View the knowledge graph (optional)
python -m cognee -ui   # Opens at http://localhost:3000
```

### Expected output from `04_evolve.py`

```
======================================================================
  STAGE 4: SELF-EVOLUTION — Redis Signal Cache + Cognee Graph Update
======================================================================

  Redis Signal Cache (real-time deal buffer):
  [+] HSET skillagents:signal:deal-001 → BuildFast WON $120K
  [+] HSET skillagents:signal:deal-002 → GlobalBank STALLED
  [✓] 2 deal signals cached in Redis (24h TTL) — immediately inspectable

  Redis keys matching 'skillagents:signal:*': 2

  BEFORE EVOLUTION — BuildFast SaaS outreach:
  [generic ICP B framing, no ROI, no proof points]

  Promoting signals to permanent knowledge graph via cognify()...
  [Cognee processes 30–90s]

  AFTER EVOLUTION — BuildFast SaaS outreach (same query):
  [ROI math, $240K ramp cost, 18-day close, CTO post reference]

  Knowledge graph grew. Every future SDR benefits from these deal lessons.
```

---

## Demo Outline (10 minutes)

| Min | What to show | Talking point |
|-----|-------------|---------------|
| 0–1 | Problem statement | "Sales teams lose $1.2M in institutional knowledge every time a rep leaves. Same objections. Same 3-month ramp. CRMs record *what* happened — they can't reason about *why*." |
| 1–3 | Stage 1: INGEST | "dlt turns nested arrays into FK edges → Cognee makes them graph edges. 84+ nodes, 228+ edges. The knowledge graph emerges from structure." |
| 3–5 | Stage 2: RETRIEVE | "GRAPH_COMPLETION, not keyword search. BuildFast CTO posted about Cursor AI → AI literacy gap → ICP B winning pattern. Three hops. Vector search misses this." |
| 5–6 | Stage 3: AUDIT | "7-section wiki. What does the AI brain actually know? The last section — Graph Edges — surfaces relationships that only exist in the graph, not in any document." |
| 6–9 | Stage 4: EVOLVE | "**THE WOW.** Deal closes → Redis HSET in 1ms. Signal immediately inspectable. cognify() runs → graph grows. Same query → richer answer. The agent just learned from a closed deal." |
| 9–10 | Cognee UI | "Every node. Every edge. The graph that gets smarter after every deal." |

---

*Self-Evolving GTM Brain — Cognee × Redis Hackathon 2026*
