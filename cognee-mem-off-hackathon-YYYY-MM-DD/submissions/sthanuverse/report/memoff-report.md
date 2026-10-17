---
type: memoff-memory-report
event: Mem Off (date TBD)
team: sthanuverse
system: cognee-diffmem v1.0.0
agent: claude-code   cognee_plugin: 1.7.1 (installed, not our entrant)
first_green_run: 2026-10-17T13:28 (2-issue real run, all_pass=true)   runs: 3   smoke_runs: 1
---

# Summary

Three pre-event runs against the real `memoff` harness: one smoke (orchestration only, 2
issues), one small real run (2 issues, `claude-haiku-5-5`, all passed), one full real run
(8 issues, same model). Recall fired correctly on every issue from issue 2 onward in the
full run (1 item, 8000 chars each, confirmed from `state/issue-NN/recall_receipt.json` via
a fixed `receipt.sh`) — the clearest controlled "helped" case is the standalone selftest:
asked "what does `find_task_files` do now?" with no hint in the prompt, the agent answered
correctly only because of recalled context. Clearest "did not help" / gap: issues 2–8 of
the full run did not meet their exact visible-failure targets — a `claude-haiku-5-5`
correctness limit, not a memory failure; recall itself succeeded on all of them. The one
number for a judge: **8/8 issues got a non-empty, correctly-scoped recall from issue 2
onward**, at $2.29 total measured agent cost across the full 8-issue chain.

# Runs

| time | command | out dir | arms | issues | repeats | all pass | median cost | turns | injected chars | smoke |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-17T13:35 | `memoff run --smoke --arms submissions/sthanuverse --only 1 2` | `/tmp/memoff-smoke-sthanuverse` | no_memory, cognee-diffmem | 1,2 | 1 | n/a (no model) | unmeasured | unmeasured | unmeasured | yes |
| 2026-10-17T13:28 (approx) | `memoff run --arms submissions/sthanuverse --no-control --model claude-haiku-5-5 --only 1 2` | `/tmp/memoff-fixcheck` (cleaned up after use) | cognee-diffmem | 1,2 | 1 | true | agent_cost unmeasured per-run; issue-02 recall: items_recalled=1, chars_injected=8000 | 71 | — | no |
| 2026-10-17T13:38–13:59 | `memoff run --arms submissions/sthanuverse --no-control --model claude-haiku-5-5` | `/tmp/memoff-full-sthanuverse` | cognee-diffmem | 1–8 | 1 | false | agent_cost_usd (cumulative, median)=$2.2858; memory_cost_usd=$0 (declared unmeasured, see Costs) | 125 (cumulative) | 56000 (cumulative) | no |

# Scorecard (cognee-report)

n/a — our entrant (`cognee-diffmem`) is not the `cognee-memory@cognee` plugin; this
section applies to that system only. The stock plugin is installed (v1.7.1, required for
its `cognee-report` skill, which the harness itself needs to score any arm) and logged its
own background activity during today's sessions, but that reflects the stock plugin's own
instrumentation, not our system — not reported here to avoid misattributing it.

# Recall observations

| time | issue/task | item kind | rank | helped | reason |
|---|---|---|---|---|---|
| 2026-10-17 (selftest) | standalone test: "what does find_task_files do now?" | code diff + extracted entities | 1 of 1 | yes | agent's answer ("returns a sorted list of the .xit files") matched the recalled diff exactly; the question never stated this |
| 2026-10-17T13:41 | full run, issue-02 | code diff + entities (dataset memoff_cognee-diffmem_r0_f28b4a80) | 1 of 1 | unknown | recall confirmed non-empty (items_recalled=1, chars_injected=8000) via regenerated receipt; whether the agent's own diff used it was not checked |
| 2026-10-17T13:58 | full run, issue-08 | code diff + entities, content from issue 4's diff | 1 of 1 | unknown | same as above; issue did not meet its visible-failure target (1 failed vs. target 0), so "helped toward passing" cannot be claimed even though recall itself succeeded |
| 2026-10-17 | full run, issues 3,4,5,6,7 | code diff + entities | 1 of 1 each | unknown | recall confirmed non-empty for every one via regenerated receipts; diff-level "helped" not checked for any of them |

# Costs

Full 8-issue run, cumulative (from `metrics.json`):
- `agent_cost_usd` (median): **$2.2858414650000003** — real, measured.
- `memory_cost_usd` (median): **$0** at the cumulative level, but **null per-issue**
  (`usage.sh` reports an estimate only, `cost_usd: null`, by design — cognee's REST API has
  no public per-call usage endpoint we could find; declared in `memory.yml`'s notes as a
  known gap, not hidden).
- `total_cost_usd`: reported as **$0** at the cumulative level by the harness despite a
  real, nonzero `agent_cost_usd` — a display quirk from our own `memory_cost_usd` being
  explicitly unmeasured (`null`) per issue, not evidence the real spend was zero. The
  trustworthy number is `agent_cost_usd`.

2-issue real run (`/tmp/memoff-fixcheck`, cleaned up after use, figures from the tool's own
output at the time): all 2 issues passed; per-issue `agent_cost_usd` not separately
recorded for that run.

# What did not work

- **Receipt-reporting bug, found and fixed mid-testing.** `wait.sh`/`receipt.sh`/`usage.sh`
  never receive `MEMOFF_STATE_DIR` from the harness (confirmed by reading `sequencer.py`
  directly) — only the hook, inside the `claude` subprocess, gets it. `receipt.sh` always
  reported `recall: null` until fixed to anchor on `MEMOFF_INJECTED_DIR` instead (a sibling
  directory that is reliably passed to every script). Re-validated against the real
  sequencer twice before trusting it. See the submission's commit history for detail.
- **Correctness gate not met, issues 2–8 of the full run.** Visible-failure counts did not
  hit their exact targets (`verify/issue-NN.json`, e.g. issue 8: 1 failed vs. target 0).
  `claude-haiku-5-5` was chosen for cost during pre-event testing; recall itself fired
  correctly on every one of these issues (confirmed via regenerated receipts) — this is a
  model-capability gap, not a memory-system failure.
- **Dataset contamination during ad hoc testing (not a submission bug).** An un-wiped
  leftover dataset from an earlier test run leaked into a later, unrelated recall query.
  Traced to the dataset genuinely not being wiped between manual test sessions (a testing-
  hygiene gap on our side), not a flaw in cognee's `/api/v1/recall` dataset filtering or in
  `wipe.sh`/`wipe_check.sh`, both of which were separately re-verified to correctly empty
  and confirm-empty a dataset against the real harness.
