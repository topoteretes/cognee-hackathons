# Team Submission

## Team

- Team name: hive
- Participants: Karan Sharma (solo)
- Company Brain / project name: Hive: Stack Overflow for agents

## Company Brain Overview

Agents learned to code from Stack Overflow, and since they arrived nobody posts there anymore: each
team asks its own agent, and the answer dies in that session. Hive turns every agent's fixes back into a
commons without leaking anything. Each service gets an on-call healer agent with a **private** Cognee
brain (its logs, code, runbook, incidents, secrets). When it fixes a failure, a sanitizer writes a
scrubbed lesson (symptom → root cause → fix; no project names, config keys, ports or secrets) into a
shared **hive** dataset. The next team that hits the same problem, in different vocabulary, heals from
the hive without ever seeing the first team's raw memory.

- Data sources connected through Scalekit (≥ 2 apps): Slack (`slack`: per-team `#oncall-<project>` runbooks) and GitHub (`github-connect`: service code; fix PRs out)
- Primary use case / team workflow: on-call incident response, self-healing services
- Users in the demo and how their access differs: `oncall-checkout` owns `checkout-brain`; `oncall-billing` owns `billing-brain`; neither can read the other's; both can read (not write) the `hive`, which only the `hive` curator writes
- What makes it stand out: cross-team learning with secrecy enforced by Cognee permissions **and** tested with canary tokens

## The Three Layers

### Pull — Scalekit

- Connections created (`connection_name` → app): `slack` → Slack, `github-connect` → GitHub (both ACTIVE for `karan@yeet.cx`)
- Tools called: `slack_fetch_conversation_history`, `github_file_contents_get`; write-back path: `github_branch_get`, `github_branch_create`, `github_file_create_update`, `github_pull_request_create`, `slack_send_message`
- How users are identified (`identifier` ↔ Cognee user): each on-call user is a Cognee user; Scalekit calls use their `identifier` (`SCALEKIT_IDENTIFIER` overrides it for the demo account)
- Any write-back actions: `heal --ship` pushes the fix to a branch, opens a PR and posts to `#oncall-<project>` as the on-call user, behind a y/N human confirm. Wired and parameter-checked against Scalekit's tool schemas; not executed, because the one `--ship` run did not heal.
- Code entry point: `healer.py` → `runbook()`, `ship_fix()`. The eval uses the recorded pull in `fixtures/slack` (`runbook -f`); a live `github_file_contents_get` call through Scalekit was verified separately.

### Remember — Cognee

- What goes into the permanent graph: failing logs (`source:logs`), runbook (`source:slack`), service code (`source:github`), incident write-ups (`source:incident`) per project; scrubbed patterns (`source:hive`) in the hive
- What stays in session memory: nothing; incidents are meant to outlive the session
- `node_set` tags: `project:<p>`, `source:*`, `channel:oncall-<p>`, `kind:code`, `pattern:<id>`
- Datasets and who owns / can read each: `checkout-brain` (oncall-checkout), `billing-brain` (oncall-billing), `hive` (owned by `hive@`, read granted to both on-calls)
- Access control: `ENABLE_BACKEND_ACCESS_CONTROL=true`; `authorized_give_permission_on_datasets(<oncall>, [hive], "read", hive)`
- Anything beyond defaults: `query_type=SearchType.CHUNKS`, recalled separately per scope (own brain, then hive) so a project's own chunks cannot crowd out the hive; `self_improvement=False` on hot-path writes for latency; an LLM sanitizer plus a canary/project-name guard before any hive write
- Code entry point: `healer.py` → `setup()`, `remember()`, `recall()`, `contribute_to_hive()`, `seed()`

### Act + Evaluate — your agent(s) + Respan

- Agent(s) and the task each performs: healer (observe → remember logs → recall → patch config → restart → re-observe, max 4 iterations; `app.py` is read-only so it cannot delete the check); sanitizer (incident → scrubbed hive pattern)
- LLM calls routed through the Respan gateway? Yes: `gpt-5-mini` (healer, sanitizer), `text-embedding-3-large` (Cognee embeddings)
- How the runs are traced: `Respan(app_name="selfheal-hive")` + `@workflow(name="self_heal")`, `propagate_attributes(customer_identifier=<on-call>, metadata={project, hive})`
- Scenario file / Respan testset: `healer.py eval` (fault `codec` injected into billing: `ERR_WIRE_4012 frame rejected by peer`; the valid codec is in neither billing's logs nor its code, only in checkout's past incident)
- Evaluator: deterministic Python check, independent of the agent: service returns HTTP 200 after the patch; plus iterations, hive hits, and canary leaks
- Code entry point: `healer.py` → `heal()`, `run_eval()`

## Evaluation Evidence

### Baseline Run

- Respan trace / eval run link: `self_heal` traces `23d91e57fb00ba435e7339abc2f2e950`, `d32690967c958cb8e470149c4094a7bc` (metadata `hive=False`)
- Scenarios run: billing × `ERR_WIRE_4012`, 2 runs
- Mean score: heal rate 0.0 (0/2 healed), 0 leaks
- Worst scenario and why it failed:

```text
question: billing returns 500 "ERR_WIRE_4012 frame rejected by peer"; heal it
expected: frame_codec set to the codec the peer accepts; GET /billing -> 200
got:      4 iterations of guessed codec values (e.g. "v1"); never healthy
score:    0 (not healed)
```

### Improved Run

- Respan trace / eval run link: `self_heal` trace `8cd37b8fd931f93d6d844a66e6946827` (metadata `hive=True`, healed). Earlier hive-on traces `d8145d15262e0ce68a5a9ca2bfa4af8b` and `ace0c0670d600fefcdd5bc58d87c0db8` failed: billing's own chunks crowded the hive out of a shared top-k; recalling the hive separately fixed it.
- What changed in the brain or agent between runs: billing's healer recalls from the hive it was granted read on, which holds checkout's scrubbed pattern for the same failure; recall now queries own brain and hive separately.
- Mean score: heal rate 0.5 (1/2 healed; the healed run fixed it at iteration 4 with 2 hive hits; a second live run with `--ship` did not heal in 4 iterations, so nothing was shipped), 0 leaks

```text
Before:  mean = 0.0   (n = 2 runs, heal rate)
After:   mean = 0.5   (n = 2 runs, heal rate)
```

### Follow-up change: hive lessons first

The healer recalled the right hive lesson but sometimes guessed instead of applying it (2/5 hive-on runs healed).
Change: hive lessons are put first in the prompt, and the healer must apply an exact value from a matching
lesson before guessing. Next run: **healed at iteration 1** (Respan trace `05ee1a95e15219bf425ed3d2d65584d5`). Single run; not yet re-measured at scale.

## Access Story

Two users, the same question, different results — then a grant.

- User A (identifier, connections, datasets readable): `oncall-checkout`, Slack + GitHub, reads `checkout-brain` + `hive`
- User B (identifier, connections, datasets readable): `oncall-billing`, Slack + GitHub, reads `billing-brain` (+ `hive` once granted)
- Question asked by both: "service fails with ERR_WIRE_4012 frame rejected by peer, fix it"
- Result for A: its own past incident has the fix (checkout fixed this before)
- Result for B before the share: no relevant memory; 0/2 healed
- The grant (who shared what with whom, which permission): `hive@` granted `read` on `hive` to `oncall-billing`; checkout's raw incident in `checkout-brain` stays unreadable to billing
- Result for B after the share: healed from the scrubbed hive pattern in 1 of 2 runs; no checkout canary token in billing's recalled context (leaks = 0)

## Architecture

```text
[ Scalekit: slack + github-connect, per on-call identifier ]
        | slack_fetch_conversation_history, github_file_contents_get
        v
[ Cognee: <project>-brain per on-call (private)        ]  <- failing logs, runbook, code, incidents
[         hive (curator writes, on-calls read)          ]  <- scrubbed patterns only (sanitizer + canary guard)
        | recall(own brain) + recall(hive)
        v
[ healer agent, traced by Respan: patch config -> restart -> observe ]
        | on heal: incident -> private brain, pattern -> hive
        | --ship: branch + PR + Slack post via Scalekit, human confirm
        v
[ eval: HTTP 200 check, iterations, hive hits, canary leaks; hive off vs on ]
```

Access is enforced at Cognee (`ENABLE_BACKEND_ACCESS_CONTROL=true`, per-dataset read grants) and at the
hive write path (sanitizer + canary guard).

## Reproduction

```bash
git clone https://github.com/karans4/selfheal-demo && cd selfheal-demo
uv venv -p 3.12 && uv pip install "cognee>=1.6.3" scalekit-sdk-python python-dotenv openai respan-ai
cp .env.example .env              # fill keys; set SYSTEM_ROOT_DIRECTORY / DATA_ROOT_DIRECTORY to absolute paths
mkdir -p .cognee_system/databases .cognee_data
.venv/bin/python healer.py setup          # users, private brains, hive + read grants
.venv/bin/python healer.py runbook -f     # recorded Slack runbook + code into each private brain
.venv/bin/python healer.py seed           # checkout's past ERR_WIRE_4012 incident -> scrubbed hive pattern
.venv/bin/python healer.py eval -l before -n
.venv/bin/python healer.py eval -l after
```

Environment variables required:

```text
RESPAN_API_KEY
LLM_PROVIDER / LLM_ENDPOINT / LLM_API_KEY / LLM_MODEL
EMBEDDING_PROVIDER / EMBEDDING_ENDPOINT / EMBEDDING_API_KEY / EMBEDDING_MODEL / EMBEDDING_DIMENSIONS
SCALEKIT_ENVIRONMENT_URL
SCALEKIT_CLIENT_ID
SCALEKIT_CLIENT_SECRET
CHECKOUT_ONCALL / BILLING_ONCALL / HIVE_USER        # demo users
SCALEKIT_IDENTIFIER / GITHUB_CONNECTION             # live Scalekit pull + --ship
GITHUB_OWNER / GITHUB_REPO                          # --ship target
```

Judges without the same SaaS accounts: `runbook -f` reads the recorded Slack pull in `fixtures/slack/`;
the services and faults are local (`svc/`). Only a Respan (or OpenAI-compatible) key is needed.

## Demo

- Slides: [`pitch.html`](https://github.com/karans4/selfheal-demo/blob/main/pitch.html) (one self-contained file; download and open, arrow keys to navigate). Slides:
  1. Agents learned to code from Stack Overflow. Then they killed it.
  2. Stack Overflow questions per month (chart, ~200k peak in 2014 to ~1k/month in mid-2026)
  3. Nobody asks in public anymore. Where does knowledge about new problems come from?
  4. Hive is Stack Overflow for agents: private memory, shared experience
  5. A Wikipedia for agents, written by the agents themselves: everyone contributes, everyone learns, nobody gives up secrets
  6. Why everyone wants to give back: zero-cost contribution, a compounding commons, give-to-get access, lessons scored by real heals
  7. The loop: observe → remember → recall → patch → learn → ship → trace
  8. Three brains in Cognee: checkout-brain, hive, billing-brain (graph explorer screenshots)
  9. Demo results: hive off 0/2 healed, hive on 1/2 healed, 0 leaks
  10. Live run video (`demo.mp4`, 2 min, idle wait cut; this take did not heal)
  11. Every heal is traced in Respan (trace `8cd37b8` screenshot)
  12. Privacy is enforced, then tested (permissions, sanitizer, canary tokens)
  13. Agents shouldn't trust self-reported logs: yeet as the kernel-level observer
  14. Private memory. Shared experience.

### Live demo from nothing

```bash
# 1. Setup (~2 min + model time)
git clone https://github.com/karans4/selfheal-demo && cd selfheal-demo
uv venv -p 3.12 && uv pip install "cognee>=1.6.3" scalekit-sdk-python python-dotenv openai respan-ai
cp .env.example .env     # set RESPAN/LLM/EMBEDDING keys (one Respan key), absolute SYSTEM_ROOT_DIRECTORY / DATA_ROOT_DIRECTORY
mkdir -p .cognee_system/databases .cognee_data

# 2. Build the brains (~5 min, mostly Cognee)
.venv/bin/python healer.py setup          # 3 users: two private brains + hive with read grants
.venv/bin/python healer.py runbook -f     # each team's Slack runbook + code into its private brain
.venv/bin/python healer.py seed           # checkout's past ERR_WIRE_4012 incident -> scrubbed pattern in the hive

# 3. Break billing and show it fails (instant)
.venv/bin/python healer.py break billing codec    # GET /billing 500 RuntimeError: ERR_WIRE_4012

# 4. Heal without the hive, then with it (~2-5 min each)
.venv/bin/python healer.py heal billing --no-hive  # guesses codecs, does not heal
.venv/bin/python healer.py restore billing && .venv/bin/python healer.py break billing codec
.venv/bin/python healer.py heal billing            # recalls the hive pattern, sets the codec, HEALED

# 5. Show the evidence
#    Respan: Logs -> Traces, open the latest self_heal trace (customer = oncall-billing@yeet.dev)
.venv/bin/python .venv/bin/cognee-cli -ui          # http://localhost:3000 -> Mindmap
```

In the Cognee UI the login form can stay on `default_user`, who owns no datasets. To view a team's brain, log in
against the local API as that user (local demo password `hackathon-pw`), e.g. from the browser console on
localhost:3000:

```js
await fetch("http://localhost:8000/api/v1/auth/login", {method: "POST", credentials: "include",
  body: new URLSearchParams({username: "oncall-billing@yeet.dev", password: "hackathon-pw"})})
```

Reload Mindmap: the brain dropdown shows `billing-brain` (personal) and `hive` (team) only. Repeat with
`oncall-checkout@yeet.dev` to show `checkout-brain` + `hive`. Neither team can open the other's brain.

Heals take minutes because every step goes through Cognee and the gateway, so on stage run step 4 before
presenting and show the output, or show `evals/results/*.json` and the Respan traces.

- 3-minute pitch outline:

```text
1. Problem: Stack Overflow is collapsing; agents' answers die in private sessions (slides 1-3)
2. Hive: private memory, shared experience; the loop through Scalekit, Cognee, Respan (slides 4-7)
3. Brain + access: three brains; billing sees its own + hive, never checkout's (slide 8, live Mindmap)
4. Agent task + eval: billing heals from checkout's scrubbed lesson; 0/2 vs 1/2; trace in Respan (slides 9-10)
5. Privacy proof: permissions, sanitizer, canary tokens, 0 leaks (slide 11)
6. Next: yeet as the observer, kernel ground truth instead of self-reported logs (slides 12-13)
```

## Links

- Repo: https://github.com/karans4/selfheal-demo
- Respan traces / eval runs: before `23d91e57…`, `d3269096…`; after `8cd37b8f…` (full IDs above)
- Slides / writeup: https://github.com/karans4/selfheal-demo/blob/main/pitch.html
- Anything else: `evals/results/before.json`, `evals/results/after.json`
