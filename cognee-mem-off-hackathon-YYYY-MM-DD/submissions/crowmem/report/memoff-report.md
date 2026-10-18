---
type: memoff-memory-report
event: Mem Off
team: crowmem
system: Crowmem 6c925b6b084430eb6e246abf5b6262a623e44056
agent: claude-code
cognee_plugin: 1.7.1
first_green_run: 2026-10-17 23:40 UTC (visible target only)
runs: 3
smoke_runs: 1
---

# Summary

One two-issue smoke run completed without calling the agent model; its zero token and cost values do not measure memory quality. A real Issue 1 cold-store probe met the visible target in 13 turns. After fixing a Bash-only observation gap, a two-issue probe met both public visible targets and injected two memories (392 characters) into Issue 2. The private grader is unavailable locally; the injection has no proven causal effect on the answer.

# Runs

| time | command | out dir | arms | issues | repeats | all pass | median cost | turns | injected chars | smoke |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-17 23:30 UTC | `memoff run --smoke --no-control --arms /entrant --only 1 2 --repeats 1 --xitkit-source /xitkit --out /runs/crowmem-smoke-2` | `/runs/crowmem-smoke-2` | crowmem | 1, 2 | 1 | no (expected for no-model smoke) | n/a (metric 0) | n/a (metric 0) | 0 | yes |
| 2026-10-17 23:36 UTC | `memoff run --no-control --arms /entrant --only 1 --repeats 1 --xitkit-source /xitkit --out /runs/crowmem-real-probe` | `/runs/crowmem-real-probe` | crowmem | 1 | 1 | yes (visible only) | unmeasured (harness) | 13 | 0 | no |
| 2026-10-18 00:04 UTC | `memoff run --no-control --arms /entrant --only 1 2 --repeats 1 --xitkit-source /xitkit --out /runs/crowmem-memory-probe` | `/runs/crowmem-memory-probe` | crowmem | 1, 2 | 1 | yes (visible only) | unmeasured (harness) | 28 | 392 | no |

# Scorecard (cognee-report)

n/a for Crowmem. The installed cognee plugin supplied the harness evaluator, not this arm's memory scorecard.

# Recall observations

| time | issue/task | item kind | rank | helped | reason |
|---|---|---|---|---|---|
| 2026-10-18 00:09 UTC | Issue 2, two-issue probe | two agent-summary memories | 1, 2 | unknown | Receipt returned two ids and the injected dump totaled 392 characters; no diff establishes that the agent used either item. |

# Costs

The smoke metrics report zero by design, an orchestration marker. For the real Issue 1 probe, `metrics.json` reports agent cost $0.0806143 and memory cost $0.004313. The two-issue memory probe reports agent cost $0.3373472 and memory cost $0.013129. Trial `total_cost_usd` remains null because the public adapter sets entrant `usage_complete` to false even when client and server sources are present. No savings are inferred.

# What did not work

- `/runs/crowmem-smoke`: the first smoke attempt stopped during `install.sh` because the pinned engine commit lacks editable-build package discovery. The submitted installer now installs dependencies from its `pyproject.toml`; `/runs/crowmem-smoke-2` completed.
- `/runs/crowmem-real`: the published Dockerfile ran Claude Code as root, which rejected the harness permission flag. The completed real probe used a local non-root runner with sudo; this runner adjustment is outside the submission.
- `/runs/crowmem-real-probe`: public harness total cost remained unmeasured despite separate agent and server costs. This is a harness accounting issue, not evidence of zero cost.
- `/runs/crowmem-full`: the first eight-issue attempt was stopped after Issue 2 because Claude used only successful Bash edits, which the selective hook ignored; the store had zero episodes. The corrected Stop hook stored a summary and the two-issue probe confirmed recall across issues.
