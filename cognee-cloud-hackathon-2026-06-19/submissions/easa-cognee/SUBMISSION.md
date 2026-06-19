# Team Submission

## Team

- Team name: Easa-Cognee (solo)
- Participants: Omid Mohajerani
- Company Brain / project name: **Easa-Cognee**

## Company Brain Overview

**Easa** is a personal business assistant that answers your phone. **Easa-Cognee** gives it a self-improving brain on Cognee, with a twist: Easa has **two sides**, and the human-in-the-loop feedback step is itself a phone call. Customers reach Easa as a receptionist; it answers from the brain and every call is scored, with gaps it couldn't answer logged. The owner calls a second line, asks "what's happening?", hears where Easa struggled, and teaches a fact or approves a behaviour change **by voice** — so the next customer call is better. You can literally *hear* the agent improve itself.

- Domain or data sources: an independent consultant's business knowledge (synthetic seed: services, hours, booking) + live call transcripts.
- Primary use case: a receptionist that answers callers from a knowledge graph and gets smarter from owner feedback.
- What makes it stand out: the feedback loop is a **voice conversation** — the owner improves the assistant just by calling it.

## The Three Operations

### Ingest

- What goes in: synthetic business facts + skill instructions, then every call's transcript.
- How it is captured: `cognee.remember(...)` via `brain/adapter.py`; seed loaded by `ingest_seed`.
- Code entry point: `brain/core.py::ingest_seed`, per-call `brain/core.py::remember_call`.

### Query + Self-improve

- How users query the brain: customers ask by phone; the assistant calls a `lookupKnowledge` tool → `/recall` → `cognee.recall(...)`.
- Where feedback comes from: a per-call scoring rubric (`brain/scorer.py`: answered-vs-deflected, language consistency, callback captured, spam declined) **and** explicit owner feedback by voice.
- How feedback updates the brain: a low score creates a `skill_feedback` proposal; on owner approval the brain applies it (`run_improvement` → `improve`) and re-renders behaviour. In parallel, call transcripts are distilled from session memory into the permanent graph so recall returns the new facts.
- Code entry point: `brain/core.py::run_improvement`, `brain/scorer.py::score_call`.

### Lint

- What "linting" means here: dedupe + **conflict detection** over the permanent graph — e.g. two different hourly rates (€120 vs €150).
- How it runs: on-demand via `/lint` (and surfaced to the owner by voice for resolution).
- Code entry point: `brain/core.py::lint`.

## Self-Improvement Evidence

Reproducible, no phone required, via the harness. Demo business: an independent consultant; the seed **deliberately omits the hourly rate** so the first call hits a gap.

### Baseline Run

- Query / task: caller asks "What's your hourly rate?"
- Result: Easa deflects — *"I don't have that yet, can I take a message?"* (gap logged).
- Score: `success_score < 0.50` (deflected).
- Recorded feedback:

```text
error_type: deflection
error_message: could not answer "What's your hourly rate?"
feedback: knowledge gap — rate not in brain; offer callback instead of generic message
success_score: 0.40
```

### Improved Run

- Query / task: same question after the owner teaches the rate by voice ("It's €150 an hour, offer a callback").
- Result: Easa answers *"€150 per hour — want a callback?"* from the brain.
- Score: `success_score >= 0.70`.
- What changed in the brain between runs: the rate fact was distilled into the permanent graph, and the deflection-handling skill was rewritten.

```text
Before:
recall("hourly rate") -> [] ; assistant deflects ; gap logged

After:
recall("hourly rate") -> ["Omid's rate is €150/hour"] ; assistant answers + offers callback
```

Reproduce: `python -m harness.improve --fake` → both scripted bad calls score `< 0.50`, generate proposals, and apply.

## Architecture

```text
[ phone call / agent turns ]
        |
        v
[ Cognee — session memory (session_id = call id) ]   <- per-call scratchpad
        |
        | distillation: durable facts promoted after the call
        v
[ Cognee — permanent graph (no session_id) ]         <- cross-call knowledge + skills
        |
        v
[ recall -> assistant answers ]
        |
        v
[ scorer -> propose -> owner approves -> improve ]
```

- `brain/` — the only module touching Cognee (`remember`/`recall`/`forget`/`improve`/`serve`/`push`), plus `core.py`, `scorer.py`, and a `fake_adapter.py` mirroring the interface for deterministic tests.
- `service/` — FastAPI on `https://cognee.voipdevops.com` (Debian 12, Caddy TLS, shared-secret auth): a voice webhook (call start + end-of-call report), `lookupKnowledge` (customer), owner tools (`reviewActivity` / `teachFact` / `applyImprovement`), and `/recall /remember /improve /lint /health`.
- **16 passing tests** (scorer, core, service, voice webhook). Live HTTPS `remember → recall` round-trip confirmed.

### Cognee Cloud (optional, rewarded)

The brain is pushed to a Cognee Cloud tenant via `cloud_push.py` (`cognee.serve(url, api_key)` + `cognee.push(...)`).

- Session memory (`session_id = call id`): raw call transcripts and per-call working notes.
- Permanent graph (no `session_id`): durable business facts (services, hours, taught rate), recurring questions, and skills.
- Distillation: after each call, durable facts are promoted from the session into the permanent graph; transient chatter is dropped.
- Reproduce: set `COGNEE_CLOUD_URL` + `COGNEE_CLOUD_API_KEY`, then `python cloud_push.py`.

## Agents / Skills

```text
Skill path(s): skills/easa-assistant.md (customer), skills/easa-owner.md (owner)
Roles:
  - Ingestor: brain/core.py::ingest_seed
  - Querier:  brain/core.py::recall_context (+ /recall)
  - Linter:   brain/core.py::lint
  - Critic:   brain/scorer.py::score_call -> brain/core.py::run_improvement
```

## Reproduction

```bash
uv venv && source .venv/bin/activate && uv pip install -e ".[dev]"
pytest -v                       # 16 tests
python -m harness.improve --fake   # before/after self-improvement, no phone
python cloud_push.py            # push the brain to Cognee Cloud (needs cloud creds)
```

Environment variables required:

```text
COGNEE_CLOUD_URL        # Cognee Cloud instance URL
COGNEE_CLOUD_API_KEY    # Cognee Cloud API key
COGNEE_LLM_API_KEY      # LLM key cognee uses
OPENAI_API_KEY          # LLM key
EASA_API_KEY            # shared-secret header for the service
```

## Demo

- Live demo: two phone numbers, on stage.
- 3-minute pitch outline:

```text
1. "Easa answers your phone and gets better every call — and you improve it just by calling it."
2. Ingest: synthetic business brain loaded into Cognee.
3. Query (before): call the customer line, ask the hourly rate -> it admits the gap, offers a callback.
4. Self-improve: call the owner line, ask "what's happening?" -> it surfaces the gap; teach it the rate by voice.
5. Query (after): call the customer line again -> it now answers the rate from the brain.
6. What's next: lint catching contradictions by voice; more skills; richer distillation.
```

## Links

- Repo: available on request (private during the event).
- Slides / writeup: this document.
