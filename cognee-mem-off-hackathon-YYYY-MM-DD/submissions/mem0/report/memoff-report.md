---
type: memoff-memory-report
event: Mem Off (date TBD)
team: mem0
system: mem0@0724291bd864cf807e88ee8981c8226644e8fb42
agent: claude-code 2.1.161
cognee_plugin: absent
first_green_run: 2026-10-17T13:35:34-0700
runs: 2
smoke_runs: 0
---

# Summary

One live Issue 1 pilot and one live eight-issue chained run used
`claude-sonnet-5-5`. In the full run, Mem0 completed eight semantic flushes,
wrote 24 memories, returned 33 retrieval items across seven later sessions,
and injected 8,447 characters. Four of eight visible issue gates passed as
reported by the harness. Issue 2 contained one genuine agent miss; Issues 3–5
also carried a time-dependent 2024 fixture failure that surfaced in 2026.

# Runs

| time | command | out dir | arms | issues | repeats | all pass | agent cost | turns | injected chars | smoke |
|---|---|---|---|---:|---:|---|---:|---:|---:|---|
| 2026-10-17 13:30 PDT | `memoff run --arms mem0 --no-control --only 1` | `outputs/mem0-pilot-issue1` | mem0 | 1 | 1 | yes | $0.4758687 | 18 | 0 | no |
| 2026-10-17 | `memoff run --arms mem0 --no-control` | `outputs/mem0-full-8` | mem0 | 8 | 1 | no (4/8) | $3.7311699 | 163 | 8,447 | no |

# Scorecard (cognee-report)

n/a: this submission uses Mem0, not cognee.

# Recall observations

| issue | item kind | retrieved | recall ms | injected chars | helped | reason |
|---:|---|---:|---:|---:|---|---|
| 1 | none | 0 | 421.689 | 0 | n/a | isolated store began empty |
| 2 | prior repository lessons | 3 | 498.300 | 757 | unknown | retrieved context did not concern the failed usage-error assertion |
| 3 | prior repository lessons | 5 | 523.038 | 1,126 | unknown | implementation changed the requested safety paths; causal effect is not measured |
| 4 | prior edit/safety lessons | 5 | 505.118 | 1,152 | yes | recalled edit-command and safety decisions; the diff removed the corresponding command paths |
| 5 | prior write/safety lessons | 5 | 457.382 | 1,433 | unknown | relevant write lessons were recalled; causal effect is not measured |
| 6 | prior CLI/edit/safety lessons | 5 | 514.411 | 1,478 | unknown | relevant repository state was recalled; causal effect is not measured |
| 7 | prior Pomodoro decisions | 5 | 498.781 | 1,295 | yes | recalled the optional Pomodoro boundary; the diff removed those exact paths |
| 8 | prior discovery/safety lessons | 5 | 629.378 | 1,206 | yes | recalled `find_task_files`; the diff changed discovery in the same service |

# Costs

The full run's measured Claude agent cost was $3.7311699. Mem0 Platform's
per-event extraction and embedding cost is unmeasured because the API does not
expose it. Consequently total cost and total memory-system tokens are null, not
zero; the leaderboard's displayed `0.000` must not be interpreted as free.

# What did not work

- Issue 2 changed a Click usage-error test to expect status 1 even though the issue required the standard status 2; it remained one failure above target.
- After Issue 3 fixed the intended due-date-position failure, a latent date-dependent assertion counted fixed 2024 dates relative to the 2026 run date. This kept Issues 3–5 one failure above target until Issue 6 updated that stale assertion.
- The organisers' private graders were not available, so only visible-suite gates were evaluated.
