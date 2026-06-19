# Team Submission

## Team

- Team name: AstroAgent
- Participants: Dmitriy Kostunin
- Company Brain / project name: AstroAgent Brain for Funding Proposal and Budget Planning

## Company Brain Overview

AstroAgent's Company Brain supports funding proposal preparation and budget planning for verifiable AI agents in astronomy and scientific control software. It keeps proposal drafts, budgets, official program facts, AstroAgent evidence, and stakeholder input up to date, which is critical while AI technology grows exponentially and proposal assumptions become stale quickly. The on-prem workflow uses Cognee, validation sandboxes, audit logs, and open-weight models served through Helmholtz Blablador, so proposal, budget, control-system, and observatory data stay inside Helmholtz-controlled infrastructure.

- Domain or data sources: AstroAgent project pages, publications, prototype notes, control-room assistance material, program and challenge guides, Info Day material, funding drafts, budget tables and assumptions, stakeholder evidence, optional GitLab issues, and official funding web pages.
- Primary use case: Prepare and maintain AstroAgent funding proposals and budgets with a repeatable, source-grounded Cognee workflow on every relevant commit.
- What makes it stand out: The brain is not just a retrieval assistant. It becomes part of the proposal and budget-planning process: it rebuilds from the repository, evaluates claims and cost assumptions against agency and deployment criteria, learns from failed review runs, lints stale or unsupported content, and opens an automatic merge request with auditable before/after evidence. The same workflow is compatible with restricted scientific infrastructure because it is on-premise and backed by open-weight models via Helmholtz Blablador.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): The implemented `cognee_manifest.yml` builds the funding proposal dataset from the proposal Markdown (`index.md`, `summary.md`, `short_summary.md`), local PDFs/DOCX, project publications, field study validation evidence, project knowledge and events, optional GitLab issue exports.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): `scripts/cognee_ingest.py` expands the manifest, extracts Markdown/text/Tex/Bib/JSON/YAML/CSV/RST plus PDF, DOCX, and official HTML/PDF URLs, snapshots official pages under `.cognee/snapshots`, and attaches source path or URL, scope, priority, freshness, SHA-256 content hash, extraction timestamp, and commit SHA. It skips unchanged sources with `.cognee/state/ingest_state.json`, can restrict local files with `--changed-paths-file`, writes JSON reports under `.cognee/reports`, stores source items in Cognee with `DataItem.external_metadata`, ingests `skills` as `content_type="skills"`, and can write compact run observations.
- Code entry point: `scripts/cognee_ingest.py`, and run in CI by the `cognee_initial_ingest` job. The runtime is built from `Dockerfile.cognee` and `docker/cognee/*` with file-backed SQLite, LanceDB, and Ladybug storage plus Blablador/OpenAI-compatible environment normalization.

### Query + Self-improve

- How users query the Company Brain: Developers run fixed proposal-review prompts locally or in CI against the on-prem Cognee instance; the same prompts can run after each relevant commit. Model calls go through Helmholtz Blablador open-weight backends when configured, and the workflow can still write deterministic local evidence without external credentials.
- Where feedback comes from (user rating, agent critic, eval, ...): A critic skill scores answers and generated edits against funding program criteria, e.g. radical long-term vision, science-to-technology breakthrough, high-risk/high-gain methodology, etc.
- How feedback updates the brain (`SkillRunEntry`, edge re-weighting, graph rewrite, ...): Failed or weak runs are recorded as `SkillRunEntry` items with error type, feedback, and success score when live Cognee is available. The workflow also writes an explicit skill-improvement proposal and re-tests the same query with the improved reviewer policy, so before/after evidence is reproducible without credentials.
- Code entry point: `scripts/cognee_improve.py` and proposal-review skills under `skills/`.

### Lint

- What "linting" means in your brain (dedupe, conflict resolution, stale pruning, ...): Detect duplicate arguments, unsupported claims, stale deadline/budget facts, inconsistent partner status, missing official-source links.
- How it runs (scheduled, on-write, on-demand): On every relevant commit, on scheduled refresh of official agency pages, and manually before proposal review meetings.
- Code entry point: `scripts/cognee_lint.py`.

## Self-Improvement Evidence

Show that the brain actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: Run `scripts/cognee_improve.py` with the default proposal-gap review query, or pass a custom `--query`.
- Result: The baseline reviewer identifies broad proposal risks but is penalized when it lacks exact source locations, official-fact separation, or a clear patch boundary.
- Score (your own metric, judge-readable): Written to `.cognee/reports/improve-<commit>.json` under `baseline.score`.
- Recorded feedback:

```text
error_type: weak_source_grounding
error_message: baseline review lacked exact source locations and explicit patch policy
feedback: negative when baseline.score is below the configured threshold
success_score: written to baseline.score in the improve report
```

### Improved Run

- Query / task: Same query as the baseline run.
- Result: The improved reviewer anchors official facts, lint findings, and patch policy to concrete source paths/lines or explicit source-required markers.
- Score: Written to `.cognee/reports/improve-<commit>.json` under `improved.score`.
- What changed in the brain between runs:

```text
Before:
  reviewer output could be useful but was too generic for an auditable proposal workflow

After:
  reviewer output must include source locations, fact type, uncertainty status, patch boundary, and residual risks
```

## Architecture

```text
[repo commit / scheduled refresh / manual run]
        |
        v
[on-prem Docker Cognee + file-backed SQLite/LanceDB/Ladybug + Blablador model endpoint]
        |
        v
[ingest manifest: funding program files, official URLs, AstroAgent evidence, deployment notes, optional issues]
        |
        +--> [session memory: ${manifest_session_prefix}-${CI_COMMIT_SHA}]
        |        raw agent turns, run observations, critic notes
        |
        +--> [permanent graph: manifest dataset]
                 durable facts, source graph, proposal skills, validated findings
        |
        v
[proposal reviewer + critic + linter skills]
        |
        v
[validation sandbox + controlled patch under proposal's working directory]
        |
        v
[GitLab bot branch and automatic MR]
```

### Cognee Cloud / On-Prem Deployment

- Deployment stance: The demo target is fully on premise. A Cognee Cloud-compatible endpoint can be used only as an internal/self-hosted service; project data, proposal drafts, and control-system context do not need to leave Helmholtz-controlled infrastructure.
- Model backend: Open-weight models are accessed through Helmholtz Blablador's OpenAI-compatible API. This keeps the workflow compatible with restricted environments while preserving the same application interface used by common LLM tooling.
- What the team writes to session memory (`session_id=...`) - raw turns, intermediate observations, per-conversation scratchpad: CI-run observations, reviewer prompts, baseline answers, critic feedback, patch-generation notes, and validation-sandbox outcomes are written with a manifest-derived commit session id.
- What goes straight to the permanent graph (no `session_id`) - durable, cross-session facts: Official agency call facts, local source summaries, proposal claims, partner status, work package mappings, criteria, and accepted skill improvements.
- How and when content is distilled from session memory into the permanent graph, inside the on-prem Cognee instance (what gets promoted? what triggers it?): A run promotes only source-backed findings that pass lint and critic thresholds. Raw chain-of-thought-like scratchpad content, failed attempts, and unsupported claims remain session-only.
- What stays session-only vs. what gets promoted: Session-only content includes transient prompts, failed patch drafts, and low-confidence critic notes. Promoted content includes source-backed proposal gaps, accepted reviewer heuristics, official call facts, and approved proposal-improvement patterns.
- Proof the brain got smarter between baseline and improved run (how distillation quality improved): The demo report contains a baseline weak review, a `SkillRunEntry`-compatible feedback object, a proposed reviewer-skill improvement, a second run with higher rubric score, and a patch artifact that can be applied to a GitLab branch or Merge Request.

## Agents / Skills (if any)

```text
Skill path(s):
  ingestor/SKILL.md          - normalize proposal evidence and preserve provenance.
  proposal-writer/SKILL.md   - draft source-grounded proposal improvements.
  proposal-critic/SKILL.md   - score proposal material against DeepRAP and Pathfinder expectations.
  linter/SKILL.md            - detect inconsistencies before opening an MR.
  mr-author/SKILL.md         - write traceable Cognee-generated MR descriptions.

Roles:
  - Ingestor: Normalizes the `proposal` dataset, keeps proposal text mutable, prefers official EIC call material on conflicts, and flags weak provenance when claims lack a local path or official URL.
  - Proposal Writer: Edits only under proposal workspace, requires each factual claim to cite a local source path, official URL, or `TODO: source required`, and keeps the proposal framed as breakthrough cognitive AI rather than generic LLM/RAG assistance.
  - Proposal Critic: Scores long-term vision, program fit, high-risk/high-gain methodology, readiness validation, consortium credibility, source grounding/freshness, impact, portfolio fit, and exploitation logic.
  - Linter: Checks missing official-call citations, conflicting deadline/budget/readiness/partner/work-package facts, stale official snapshots, duplicated arguments, overclaims, and proposed edits outside workspace.
  - Merge Request Author: Produces merge request descriptions with the ingested source set, queries and checks run, before/after critic scores when available, files changed, rationale, before/after evidence, residual risks, reviewer checklist, and reproduction commands.

Execution:
  - `scripts/cognee_ingest.py` ingests workspace with `content_type="skills"` into the same durable dataset as the proposal evidence.
  - There is no separate generic querier skill in the mgmt implementation; fixed proposal-review queries run against Cognee and are evaluated by the critic skill.
```

## Reproduction

Commands to reproduce your demo:

```bash
# Build the local Cognee image
docker build -f Dockerfile.cognee -t mgmt/cognee:local .

# Run ingest in the local Cognee image
docker run --rm \
  -e LLM_API_KEY="${LLM_API_KEY:-}" \
  -e BLABLADOR_ENDPOINT="${BLABLADOR_ENDPOINT:-}" \
  -e BLABLADOR_MODEL="${BLABLADOR_MODEL:-}" \
  -e HZDR_GITLAB_TOKEN="${HZDR_GITLAB_TOKEN:-}" \
  -v "$PWD:/workspace" \
  -w /workspace \
  mgmt/cognee:local \
  python scripts/cognee_ingest.py --manifest funding/<year>/<program>/cognee_manifest.yml

# Reproducible review, lint, and patch artifacts
python scripts/cognee_lint.py --target funding/<year>/<program>
python scripts/cognee_improve.py --target funding/<year>/<program>
python scripts/cognee_patch.py --target funding/<year>/<program>

# Optional: apply the generated review artifact to a branch and open an MR
python scripts/cognee_patch.py --target funding/<year>/<program> --apply --output-branch --push --create-mr
```

Environment variables required:

```text
COGNEE_CLOUD_URL    # optional, internal/self-hosted Cognee-compatible endpoint URL
COGNEE_API_KEY      # optional, internal Cognee API key
LLM_API_KEY
BLABLADOR_ENDPOINT  # Helmholtz Blablador OpenAI-compatible endpoint
BLABLADOR_MODEL     # open-weight model served by Blablador
HZDR_GITLAB_TOKEN   # optional Blablador/API token
GITLAB_URL          # required only with --create-mr
GITLAB_PROJECT      # required only with --create-mr
GITLAB_BOT_TOKEN    # required only with --create-mr
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: :-(
- 3-minute pitch outline:

```text
1. Problem / idea
   AstroAgent builds verifiable AI agents for astronomy and scientific control software, but funding and deployment arguments go stale quickly because call facts, project evidence, partner status, and evaluator-facing claims live in different places.

2. Ingest demo
   Show the manifest ingesting, official funding program pages, local PDFs, AstroAgent publications/prototypes, and project evidence into an on-prem Cognee instance.

--- we are here

3. Query demo (before improvement)
   Ask for proposal gaps and show a baseline answer with weak source grounding.

4. Self-improve step
   Record critic feedback with SkillRunEntry and show a proposed improvement to the proposal-review skill, using open-weight models through Helmholtz Blablador.

5. Query demo (after improvement)
   Run the same query, show a higher score and a source-grounded patch limited to proposal workspace.

6. What is next
   Keep the brain on premise, run it on every relevant commit, and let GitLab open automatic MRs for proposal improvements with a complete source and validation trail.
```

## Links

- Repo: not open-source yet
- Project page: `https://astroagent.zeuthen.desy.de`
- Slides / writeup:
- Anything else:
