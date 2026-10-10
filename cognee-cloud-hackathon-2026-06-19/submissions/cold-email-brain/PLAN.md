# Cold Email Brain — Cognee Cloud Hackathon Plan

**Event:** Cognee Cloud Hackathon · Berlin · 2026-06-19, 6pm–10pm
**Team:** Morris Neiland (solo, +Claude as co-pilot)
**Project name:** Cold Email Brain — *"a brain that learns which cold emails actually land"*
**Submission deadline:** 9:00pm · Demo: 9:15pm · 3 minutes on stage

---

## 1. Winning theory

Five things judges (Cognee engineers) will reward, ranked:

1. **A visible before/after delta** on stage — email v1 demonstrably bad, email v2 demonstrably better, in the same demo run.
2. **A clever distillation policy** — explicit rule for what gets promoted from session memory → permanent graph, not just "we dumped everything in".
3. **Two-skill self-improvement loop** — both the writer *and* the critic improve. Most teams will only have one.
4. **Cognee Cloud connected from the start** (`cognee.serve(...)`) — free score bump for the "Best Use of Cognee Cloud" bonus.
5. **A real human story** — Morris is an actual BDR demoing his actual outbound problem. Authenticity that other teams can't fake.

## 2. The one-line pitch

> "I'm a BDR. I write 80 cold emails a day. Every BDR tool stores templates — mine stores *learnings* and rewrites itself every time a prospect ignores me. Watch."

## 3. Architecture

```text
                    [ Morris types prospect persona ]
                                 │
                                 ▼
   ┌─────────────────────────────────────────────────────────┐
   │                  Cognee Cloud instance                  │
   │                                                          │
   │   ┌──────────────────────────────────────────────┐      │
   │   │  SESSION memory (session_id=prospect_xyz)     │      │  hot, per-prospect
   │   │  - raw current email draft                    │      │  scratchpad
   │   │  - critic's per-run feedback                  │      │
   │   │  - recent SkillRunEntry events                │      │
   │   └──────────────────┬───────────────────────────┘      │
   │                      │                                  │
   │  distillation rule: promote only if pattern             │
   │  fires across ≥3 prospects with avg score ≥0.7          │
   │                      │                                  │
   │                      ▼                                  │
   │   ┌──────────────────────────────────────────────┐      │
   │   │  PERMANENT graph (no session_id)              │      │  durable
   │   │  - learned outbound patterns                  │      │  cross-prospect
   │   │  - skill bodies (writer + critic)             │      │  knowledge
   │   │  - prospect-industry → hook patterns          │      │
   │   └──────────────────────────────────────────────┘      │
   └─────────────────────────────────────────────────────────┘
                                 ▼
              [ writer skill → email v1 → critic scores ]
                                 │
                  if score < 0.7 → SkillRunEntry → propose → apply
                                 │
                                 ▼
              [ writer skill v2 → email v2 → critic scores ]
                                 │
                                 ▼
              [ visible diff on stage; audience hears delta ]
```

## 4. Data corpus

**Real (~20 from Morris's Gmail, extracted via Gmail MCP):**
- 10 cold sends from June 5 ("Frisst Bürokram noch viel Zeit?") — all silent or auto-responder
- 1 fully cold ("HandwerkerCRM für Die [anonymized-prospect]", Dachdecker Lüneburg) — silent
- ~10 post-call follow-ups ("wie versprochen") — mostly silent, one forwarded internally ([anonymized-prospect])
- **Key insight already in the data:** the only positive signal came from a post-call email. Cold-without-call = silence.

**Synthetic (~80 generated via the LLM at runtime):**
- Spread across industries: Dachdecker, Maler, Fliesenleger, Tischler, Elektriker, HVAC, Sanitär
- Spread across outcomes: ignored (60%), declined (15%), replied positive (25%)
- Hook variations: pain-point cold, post-call follow-up, complimented-their-reviews, mutual-connection
- Score labels: derived from outcome (ignored=0.2, declined=0.4, mild reply=0.6, positive=0.85, demo-booked=0.95)

**Combined:** `data/seed.json` — 100 tuples of `{persona, hook_type, body, outcome, score}`

## 5. Two skills

### `my_skills/writer/SKILL.md`
> Write a cold email for a German Handwerker prospect. Use patterns from the brain. Match trade-specific pain. If a call was attempted, reference it. Short, conversational, one clear CTA.

### `my_skills/critic/SKILL.md`
> Score a cold email 0–1. Criteria: trade-specific pain match (0.3), prior-touchpoint reference if applicable (0.2), CTA quality (0.2), length under 150 words (0.1), tone (0.2). Return JSON `{score, criteria_breakdown, fix_suggestion}`.

Both skills get rewritten via `SkillRunEntry → propose → apply`. The critic improving is the under-the-radar move that signals technical depth.

## 6. The distillation rule (our unique angle)

In `brain/ingest.py` and `brain/feedback.py`:

```python
# Pseudo-policy:
# Session memory: everything raw (current draft, critic feedback, run logs)
# Promotion to permanent graph requires:
#   - same pattern observed across ≥3 distinct prospects
#   - average outcome score ≥0.7
#   - not contradicted by ≥2 negative observations within last 14 days
```

This stops the brain from overfitting to one quirky prospect and is the design choice we'll name on stage. The README's example loop does *not* have this — judges will hear it as a thoughtful extension.

## 7. Build sequence (3-hour budget)

| Block | Time | What | Output |
|---|---|---|---|
| **A** | 6:00–6:20 | `uv venv`, install `cognee==1.2.0.dev1`, `pip install streamlit python-dotenv`, paste Cloud + LLM keys, hello-world `remember/recall` against Cloud | Cognee talking, Cloud connected |
| **B** | 6:20–6:50 | Extract real emails from Gmail → `data/real_emails.json`. Generate 80 synthetic via Claude → `data/synthetic.json`. Combine → `data/seed.json` | 100-tuple corpus ready |
| **C** | 6:50–7:20 | Write the two SKILL.md files. Build `brain/ingest.py` — load seed into Cognee with the session/graph split + distillation rule | Brain is fed |
| **D** | 7:20–8:00 | Build `brain/writer.py`, `brain/critic.py`, `brain/feedback.py`. End-to-end smoke test: prospect → v1 → score → SkillRunEntry → propose → apply → v2 → score. **Engineer the delta** until v1≈0.3 and v2≈0.8 reliably for the demo persona | Loop works |
| **E** | 8:00–8:35 | `ui/app.py` — Streamlit: prospect input → Generate → email + score card → "Train on this" button → SKILL.md diff inline → Regenerate → v2 + score | Demo-able |
| **F** | 8:35–8:50 | `brain/lint.py` (dedupe + prune, ~30 lines). `cognee.push("cold-email-brain")`. Screenshot v1 + diff + v2 | Cloud + lint done |
| **G** | 8:50–9:00 | Fill in `SUBMISSION.md` with before/after evidence + push commit | Submitted |
| **H** | 9:00–9:15 | Rehearse 3-min demo twice. Lock the opener and the kicker. | Pitch-ready |

**Slip plan:** if behind at 8:00, kill the UI and demo from a terminal with nice print statements. If behind at 8:35, skip lint code (just describe it in SUBMISSION.md). Never skip rehearsal.

## 8. Demo script (locked at rehearsal, but draft now)

```text
0:00–0:15  Hook (1 sentence + "watch")
0:15–0:35  The pile — show graph UI / corpus size, name the insight from real data
0:35–1:25  Run #1: type persona, generate v1, read it, show critic score 0.3
1:25–2:05  Train: click button, show SkillRunEntry + SKILL.md diff inline
2:05–2:45  Run #2: regenerate, read v2, show critic score 0.8 — audience hears delta
2:45–3:00  Kicker: "Imagine 50 BDRs sharing one brain. Karpathy's LLM Wiki for sales."
```

**Demo persona (locked):**
> *Dachdecker in Köln, 6 Mitarbeiter, papierbasierte Auftragsabwicklung, telefonisch nicht erreicht.*

## 9. Risk register

| Risk | Mitigation |
|---|---|
| Cognee 1.2.0.dev1 has API surprises (README mentions caveats around skill names canonicalizing, `remember()` returning dict not object) | Code defensively — read `items` via both `result["items"]` and `result.items`; pull skill name from the ingest response, don't hardcode |
| Cloud connection flaky | Develop locally; `cognee.push(...)` at the end gets the bonus either way |
| v2 doesn't sound clearly better than v1 in rehearsal | Engineer the delta — adjust the synthetic data + the writer skill's base prompt until the gap is audible; this is more important than any other polish |
| Streamlit refuses to start in 35 min | Fallback: Python script with `rich` terminal output, equally demoable |
| Run out of time before submission | Lint can be 30 lines + a sentence in the writeup; rehearsal is non-negotiable |
| The "called first" insight doesn't land | Have a 2nd backup insight prepared: "trade-specific pain beats generic 'efficiency' framing 4:1" |

## 10. Submission checklist (from `templates/SUBMISSION.md`)

- [ ] Idea writeup
- [ ] Code in this folder (pushed to a GitHub repo)
- [ ] Before/after evidence (screenshots of v1, the diff, v2)
- [ ] Note Cognee Cloud usage (`serve` + `push`) for the bonus
- [ ] 3-min demo (live)
- [ ] Submission as PR or team folder per the template

## 11. What I (Claude) own vs. what Morris owns

**I own:** all code, debugging, data extraction, synthetic generation, distillation logic, UI, lint, push, submission writeup draft.

**Morris owns:**
1. **Paste the kickoff API keys** the moment you get them (Cognee Cloud URL + API key + LLM_API_KEY).
2. **Pick the moment** when v1 is "embarrassing enough" and v2 is "clearly better" in dev — your sales ear is sharper than mine. We'll dial it in together at ~7:50pm.
3. **Deliver the pitch live.** I'll write the script; you sell it.
4. **One sanity check on the synthetic data** — I'll show you 5 examples around 6:40pm; if anything sounds fake-AI, you flag it.

---

*Next: install Cognee, wait for kickoff keys, extract Gmail data in parallel. Will report after each block (A–H).*
