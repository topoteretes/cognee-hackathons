# Agent Failure Mode Wiki — Submission

Team **Failure Wiki** (Jiyun Kim) submission for the
**Cognee × Redis 2026-05-16 AI-Memory hackathon**.

- **Project repo:** [Jiyungi/agent-failure-mode-wiki](https://github.com/Jiyungi/agent-failure-mode-wiki)
- **Submission writeup:** [`SUBMISSION.md`](SUBMISSION.md)
- **Top-level README:** [Jiyungi/agent-failure-mode-wiki#agent-failure-mode-wiki](https://github.com/Jiyungi/agent-failure-mode-wiki#agent-failure-mode-wiki)

## TL;DR

Operational-memory layer that any long-horizon or multi-agent system can
attach to so it stops re-discovering the same failures every run.
Failures become typed graph nodes (`FailureMode`, `RecoveryAction`,
`AgentQuery`, `SolutionLog`, `LintIssue`, `SessionRun`). Redis is the
session-memory tier (RedisVL `failure_wiki` index plus a per-session
event list). Cognee is the durable graph tier, loaded with structured
`add_data_points` so the demo never blocks on `cognify()`. A
propose-then-apply loop promotes recoveries up a confidence ladder
(0.4 → 0.7 → 1.0); lint flags everything below `1.0`.

## Three-minute demo

```bash
git clone https://github.com/Jiyungi/agent-failure-mode-wiki
cd agent-failure-mode-wiki
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r demo/requirements.txt
cp demo/.env.example demo/.env  # fill OPENAI_API_KEY + Redis fields
bash demo/record_demo.sh
```

Visual companion:

```bash
python -m http.server 8765
# open http://127.0.0.1:8765/demo/visual/
```

The visual reads `demo/.demo_state/wiki/manifest.json`, so it always
reflects the latest run: failure records, agent queries, solution logs,
proposals (applied vs. pending), lint findings, the live `session_id`,
and the Cognee structured-graph status.

## Evidence

Two committed snapshots prove the loop fires end-to-end against the
live Redis Cloud + Cognee + OpenAI stack:

- [`demo/evidence/manifest_before.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_before.json) — end of run #1: FM-007 just discovered, `confidence=0.7`, lint=1, Cognee `ready` 28 nodes / 36 edges.
- [`demo/evidence/manifest_after.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_after.json) — end of run #2 (no reset): FM-007 promoted to `1.0`, lint=0, Cognee `ready` 29 nodes / 40 edges.

## Skill

Skill artifact in the brief's frontmatter format lives at
[`my_skills/failure-triage/SKILL.md`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/my_skills/failure-triage/SKILL.md).
The propose-then-apply loop is implemented in
[`demo/self_improve.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/self_improve.py)
because cognee `0.5.6` (pinned by the Redis vector adapter `0.1.4`)
does not yet expose `improve_skill` / `SkillRunEntry`.
