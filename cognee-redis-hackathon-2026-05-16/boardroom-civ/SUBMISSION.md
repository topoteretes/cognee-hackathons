# Team Submission

## Team

- Team name: Boardroom Civ
- Participants: dyyfk
- Wiki / project name: **Boardroom Civ — a playable LLM Knowledge Wiki**

## Wiki Overview

Boardroom Civ is a turn-based startup-strategy simulator whose state *is*
the LLM Wiki. The player is the leadership team of a fictional AI startup
(Northstar Labs). Each round the world fires an event — a competitor
open-sources a model, a regulator drops a compliance framework, a cloud
bill spikes — the player picks a posture, and the agent (a) writes the
consequences into a Markdown wiki the player can read, *and* (b) ingests a
structured document into a Cognee knowledge graph that the next round's
advisor and lint pass query back. When a game ends, the agent writes a
structured post-mortem entity into the graph, so the **next** game's
advisor recalls it and proposes compound moves that avoid the prior
failure mode. The wiki literally gets smarter game-over-game.

- Domain or data sources: synthetic — canon event timeline + each round's
  resolved decision (action, posture, world reaction across 5 stakeholder
  groups, new assumptions, chaos events, capital deltas). At end-of-game,
  a structured post-mortem (root-cause chain, what-killed-us, lessons,
  compound moves that would have worked) is ingested as a distinct entity
  type so the graph can cite it cross-session.
- Primary use case: agent-maintained living wiki for a strategy game, but
  the architecture is a general pattern for any agent that needs to
  remember *why* it made past choices, not just what it said.
- What makes it stand out:
  1. The wiki is the product, not a side artifact. The player reads it.
  2. Self-improvement is **cross-session**: prior games' post-mortems
     change the next game's recommendations and the advisor cites them
     inline (`[g1-postmortem]`).
  3. Three operations are wired to one Cognee call each — `remember`,
     `recall`, and a recall-driven audit — kept honest by a deterministic
     offline fallback so the demo never breaks if the sidecar dies mid-show.

## The Three Operations

### Ingest

- **What goes in:** one structured document per resolved round
  (event, action, posture, 5-channel world reaction, new assumptions,
  wiki patches, optional chaos event), plus one **post-mortem entity per
  finished game** (outcome, root-cause chain, what-killed-us, lessons,
  compound moves that would have worked).
- **How it is captured:** the Express server fires-and-forgets a payload
  to a Python FastAPI sidecar that runs `await cognee.remember(doc)`.
  Cognee's `remember` runs add + cognify + improve in one call — entities
  and edges are extracted automatically by an Anthropic LLM (via
  litellm), embedded with local fastembed, and stored in SQLite +
  LanceDB + KuzuDB on disk.
- **Code entry points:**
  - Document formatting: [`cognee_sidecar/main.py`](https://github.com/dyyfk/boardroom-civ/blob/main/cognee_sidecar/main.py) — `_payload_to_document` (per-round) and `_postmortem_to_document` (per-game, tagged `[POST-MORTEM · Game N]` so cross-game queries surface it distinctly).
  - HTTP route: same file — `POST /memory/ingest` and `POST /memory/postmortem`.
  - Express client: [`server/cognee.ts`](https://github.com/dyyfk/boardroom-civ/blob/main/server/cognee.ts) — `ingestRound()` (fire-and-forget) and `ingestPostMortem()`.

### Query + Self-improve

- **How users query the wiki:** the player clicks **Ask Company Wiki** in
  the Take Action modal. The server pulls two slices from Cognee in
  parallel — a generic recall for the current event, and an explicit
  post-mortem recall — and feeds both to Claude as `[memN]` /
  `[gN-postmortem]` evidence the advisor must cite when it grounds a
  recommendation. The advisor returns a compound playbook (primary
  canon move + 1–2 parallel moves + hedge + pivot triggers + cited
  lessons), and crucially **never sees chaos events** — that's the
  built-in blind-spot the demo calls out.
- **Where feedback comes from:** two loops.
  1. **Within a game:** every resolved round is ingested as new
     evidence, so the next advisor call has strictly more context. The
     advisor's `rationale` cites `[memN]` excerpts that drove the rank.
  2. **Across games:** at end-of-game the agent writes a structured
     post-mortem and ingests it. The next game's advisor recalls it and
     its compound moves are *required* to address one of the prior
     failure modes (`lessonsCited` must be non-empty when post-mortem
     excerpts exist).
- **How feedback updates the wiki:** post-mortem entities are tagged
  `[POST-MORTEM · Game N]` in the document header so semantic recall in
  later games surfaces them distinctly from per-round entries. Cognee's
  `cognify` step extracts named entities and edges (failure modes,
  named decisions, root-cause chains) so future queries can graph-walk
  across games, not just keyword-match.
- **Code entry points:**
  - Advisor: [`server/agent.ts`](https://github.com/dyyfk/boardroom-civ/blob/main/server/agent.ts) — `agentAdvisor()`. Look for the `recallQuery` (current-event slice) and the explicit `POST-MORTEM lessons from prior games...` query (cross-game slice).
  - Recall client: `queryMemory()` in `server/cognee.ts` → `POST /memory/query` → `await cognee.recall(query)` in `cognee_sidecar/main.py`.
  - Post-mortem generation: `agentPostMortem()` in `server/agent.ts`; it returns a structured object **and** ingests it via `ingestPostMortem()`.

### Lint

- **What "linting" means here:** the agent looks for contradictions
  between the company snapshot, the assumption set, the decision log,
  and the recent world reactions; flags unsupported claims; surfaces
  orphan entities (an entity exists in the graph but no recent decision
  links to it); and proposes specific patches. Findings are scoped to a
  wiki section (`company-profile`, `assumptions`, `decision-log`, etc.)
  with severity `info` / `warn` / `error` and a one-sentence suggested
  fix. The lint pass is graph-level *and* Markdown-level — both layers
  vote.
- **How it runs:** on-demand. The player clicks **Run Lint** in the top
  bar; the server first calls `cognee.recall(audit_query)` for a graph-
  side audit, then feeds those findings to Claude as `[gN]` evidence
  alongside the rendered Markdown wiki.
- **Code entry points:**
  - Lint orchestrator: `agentLint()` in [`server/agent.ts`](https://github.com/dyyfk/boardroom-civ/blob/main/server/agent.ts).
  - Graph audit: `auditMemory()` in `server/cognee.ts` → `POST /memory/audit` in `cognee_sidecar/main.py`, which sends a fixed audit prompt to `cognee.recall`.

## Self-Improvement Evidence

The strongest before/after in Boardroom Civ is the **cross-game
post-mortem loop**: Game 1 dies, the agent writes a structured
post-mortem, the graph gets one new entity, and Game 2's advisor — on
the same canon event — proposes a measurably different compound move
because it now cites the prior failure mode.

### Baseline Run

- **Query / task:** Game 1, Scene 1 ("GPT-4.5 launches; competitive
  pressure spikes"). Click **Ask Company Wiki**. Cognee graph is empty
  (`ingest_count = 0`). Advisor has only the seeded wiki to reason from.
- **Result:** advisor returns the canon "Raise pre-seed" recommendation
  with generic compound moves ("be careful with hiring", "talk to design
  partners"). `lessonsCited: []`. The player follows the recommendation,
  hits a chaos event two rounds later (cloud bill spike), runs out of
  runway, and the game ends with `outcome: "dead"` around round 5–6.
- **Score (judge-readable):** `lessonsCited.length = 0`,
  `compoundMove.specificity = generic` (no named dollar amounts,
  vendors, or deadlines), advisor `rationale` cites zero `[memN]` or
  `[gN-postmortem]` excerpts. Northstar dies.
- **Recorded feedback:**

```text
error_type:     missed_failure_mode
error_message:  Advisor proposed no specific hedge against cloud-cost shock; no prior-game evidence to cite.
feedback:       Cash crunch + sequencing (raise BEFORE wedge) killed us; future advisor must propose them concurrently and lock compute.
success_score:  0 / 1  (game ended in death)
```

That feedback is captured **automatically** at game-over by
`agentPostMortem()` in `server/agent.ts` — the model writes a structured
post-mortem object, and the server ingests it via `ingestPostMortem()`
before the next game starts.

### Improved Run

- **Query / task:** Game 2, same Scene 1, same canon event, same seeded
  company profile. **Reset** clears the in-game state but **not** the
  Cognee graph (the post-mortem entity from Game 1 persists). Click
  **Ask Company Wiki**.
- **Result:** advisor still recommends "Raise pre-seed" as the primary,
  but the compound playbook now reads (paraphrased — exact text varies
  per run):
  > Primary: Raise pre-seed. **Combine with:** lock a 90-day H100
  > reservation at ~$40k *before* the round closes (Game 1 died from a
  > cloud-cost shock 2 rounds in); start design-partner conversations
  > *in parallel*, not after raise close. **Hedge:** if compute slot
  > falls through, switch to a sub-scale Bedrock pilot. **Pivot trigger:**
  > if pre-seed term sheet slips past 30 days, freeze new hiring.
  > `lessonsCited: [{ ref: "g1-postmortem", text: "Raised before
  > locking compute → cash crunch + competitor wedge → dead by R5." }]`
- **Score:** `lessonsCited.length ≥ 1`, compound move names a dollar
  amount and a deadline, advisor `rationale` cites `[g1-postmortem]`
  explicitly. The same simulated chaos event in round 3 no longer ends
  the game — the hedge fires.
- **What changed in the wiki between runs:**

```text
Before:
  cognee_sidecar ingest_count = 0
  graph entities: (none)
  post-mortem entities: (none)
  advisor lessonsCited: []
  advisor rationale: cites only seeded wiki sections

After:
  cognee_sidecar ingest_count = 6  (5 rounds + 1 post-mortem)
  graph entities: ~30 (event nodes, decision nodes, stakeholder reactions,
                      assumption nodes, 1 post-mortem entity)
  post-mortem entities: 1   (tagged "[POST-MORTEM · Game 1]")
  advisor lessonsCited: [{ ref: "g1-postmortem", text: "..." }]
  advisor rationale: explicitly cites [g1-postmortem] when proposing
                     concurrent raise + compute lock
```

In the UI you can watch this happen in real time: open the Living Wiki
drawer, watch the **Memory Graph** badge climb from `0 rounds ingested`
to `6 rounds ingested · NN KB`, then reset the game and watch the
advisor's playbook in Game 2 cite `[g1-postmortem]` inline.

## Architecture

The hackathon's canonical pattern is **Redis as session memory,
distilled into Cognee's permanent graph**. Boardroom Civ implements the
*spirit* of that split — hot per-game state vs. durable cross-game
graph — without a literal Redis process. We are documenting the mapping
honestly:

```text
[player turn — click Take Action]
        |
        v
[ Zustand store (localStorage)  ──  session memory ]
   raw decisions, in-flight wiki Markdown,
   per-game capital/runway/branch state
        |
        | distillation = end-of-round resolve
        | (server/agent.ts → agentResolve)
        v
[ Cognee knowledge graph  ──  permanent memory ]
   structured round entities, assumption nodes,
   stakeholder-reaction edges, post-mortem entities
        |
        v
[ recall on next advisor / lint call ]
        |
        v
[ feedback -> improve loop ]
   on game-over: agentPostMortem() writes a
   structured post-mortem entity into the graph,
   so the NEXT game's advisor recalls it
```

### Redis-as-session-memory (honest mapping)

We do not run a separate Redis process. The session-memory *role* is
filled by the in-browser Zustand store (`src/state/store.ts`, persisted
to `localStorage` under `boardroom-civ:v1`) and the per-request scratch
state in the Express resolver. The permanent-memory role is filled by
Cognee. Concretely:

- **Written into session memory (Zustand / localStorage):** every player
  action, posture, the in-flight Markdown wiki sections the user is
  reading, capital snapshots, branch state. This is hot and per-game.
- **Distilled into Cognee at round resolution:** a single structured
  document per round — event, action, world reaction across 5
  stakeholder channels, new assumptions, wiki patches, optional chaos
  event. The distillation step is `_payload_to_document()` in
  [`cognee_sidecar/main.py`](https://github.com/dyyfk/boardroom-civ/blob/main/cognee_sidecar/main.py)
  followed by `await cognee.remember(doc)`.
- **What stays in session vs. promoted:** raw Markdown rendering and
  branch UI state stay in Zustand. Anything an advisor or lint pass
  might need to cite across rounds (or across games) is promoted to
  Cognee. Post-mortems are the highest-signal promotion: one structured
  entity per finished game, tagged so cross-session recall surfaces it.
- **How distillation quality improved between runs:** Game 1 ingests
  per-round documents only — keyword recall works but the graph has no
  causal chain. Game 1's *post-mortem* adds the missing causal chain
  (root-cause ordering, what-killed-us, compounds-that-would-have-worked)
  as a single dense entity. Game 2's advisor recall finds that one
  entity first and grounds its compound playbook in it. The
  distillation that mattered most wasn't more rounds — it was the
  post-mortem schema.

> **Honest note for the judges:** we picked the as-is architecture over
> wiring in a literal Redis process during the hack. Swapping Zustand
> for Redis would be a ~30-min change (the data shape is already
> distillation-friendly) but doesn't change the loop. If that's a hard
> requirement we're happy to add it post-event.

## Agents / Skills (if any)

No skill packs. Two LLM agents wired directly to Cognee:

```text
Roles:
  - Ingestor:  cognee_sidecar (Anthropic via litellm) — runs cognify on
               each round + post-mortem document.
  - Querier:   agentAdvisor() in server/agent.ts — pulls cognee.recall
               slices and produces compound playbook citing [memN] /
               [gN-postmortem].
  - Linter:    agentLint() in server/agent.ts — pulls cognee.recall
               audit findings, votes against Markdown wiki, returns
               severity-scoped findings.
  - Critic:    agentPostMortem() in server/agent.ts — writes the
                structured post-mortem the next game will learn from.
```

## Reproduction

Prerequisites: Node 18+, `uv` (`brew install uv` on macOS), an Anthropic
API key.

```bash
git clone https://github.com/dyyfk/boardroom-civ
cd boardroom-civ
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY=sk-ant-...
npm install
npm run dev
# open http://127.0.0.1:5180/
```

`npm run dev` boots three processes concurrently: Vite on 5180 (web),
Express on 5181 (agent endpoints), and the Cognee FastAPI sidecar on
5182 via `uv run --with-requirements`. First cold start downloads
`cognee` + ~130 transitive deps + the local embedding model (30–90s).
Subsequent boots are instant.

Demo loop (3 min):

1. Resolve Scene 1 ("Raise pre-seed", Balanced).
2. **Ask Company Wiki** on the GPT-4.5 event — note `lessonsCited: []`.
3. Resolve 3 more rounds. Watch the Memory Graph badge in the Living Wiki
   drawer climb (`0 → N rounds ingested`).
4. **Run Lint** — agent returns findings citing `[gN]` graph evidence.
5. Play until Northstar dies. End-of-game modal shows the post-mortem
   the agent just ingested.
6. **Reset** — Zustand wipes, **Cognee graph persists**.
7. Replay Scene 1 → **Ask Company Wiki** — advisor now cites
   `[g1-postmortem]` and proposes a concrete compound move.

Environment variables required:

```text
ANTHROPIC_API_KEY     # reused by both the game's Claude calls and Cognee's litellm
ANTHROPIC_MODEL       # optional, defaults to claude-opus-4-7
COGNEE_LLM_MODEL      # optional, defaults to claude-haiku-4-5-20251001
COGNEE_SIDECAR_URL    # optional, defaults to http://127.0.0.1:5182
COGNEE_SIDECAR_PORT   # optional, defaults to 5182
```

Embeddings are bundled (fastembed, MiniLM-L6-v2, 384-dim) — no second
key. Graph data lives in `cognee_sidecar/.data/` and
`cognee_sidecar/.system/` (both gitignored). Delete either folder for a
hard reset.

If the sidecar is down or the key is missing every Cognee call silently
no-ops and the game falls back to a deterministic offline simulator in
`server/fallback.ts`. The demo cannot break because Cognee is offline.

## Demo

- **Live demo:** local instructions above. Presented live on stage at the
  3-minute slot; no pre-recorded video.
- **3-minute pitch outline:**

```text
1. Problem / idea           Karpathy's LLM Wiki is correct but boring to
                            *watch*. Boardroom Civ turns it into a
                            playable agent-memory demo.
2. Ingest demo              Resolve a round. Watch the Memory Graph
                            badge tick from "0 rounds ingested" → "1".
3. Query (before improve)   Game 1, Scene 1, Ask Company Wiki. Generic
                            compound move. lessonsCited: [].
4. Self-improve step        Play Game 1 to a death. Show the post-mortem
                            modal. The agent just wrote a structured
                            failure entity into the graph.
5. Query (after improve)    Reset → Game 2 → same Scene 1 → Ask Company
                            Wiki. Advisor now cites [g1-postmortem]
                            inline and proposes a *specific* compound
                            (named $ amount, deadline, hedge, pivot
                            trigger).
6. Lint as the polish step  Run Lint. Findings cite [gN] graph evidence
                            against the Markdown wiki — the agent
                            critiques its own memory.
7. What's next              Multi-company tournaments; structured edge
                            types per failure mode; replace
                            Zustand-as-session-memory with literal
                            Redis to match the canonical pattern.
```

## Links

- Repo: https://github.com/dyyfk/boardroom-civ
- Slides / writeup: this SUBMISSION.md is the writeup. The repo's
  [README.md](https://github.com/dyyfk/boardroom-civ/blob/main/README.md)
  has a deeper architecture walkthrough including the Cognee sidecar
  process layout and the soft-fail / fallback strategy.
- Reference inspirations:
  - [Karpathy's LLM Wiki gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
  - [Cognee](https://www.cognee.ai/) — the agentic memory engine
  - [Hackathon event brief](https://luma.com/uhda61yp)
