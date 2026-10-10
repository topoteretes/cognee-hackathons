# Implementation Decision Log — Cognee Company Brain

## Locked Decisions (Grill Output)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Architecture** | 1C hybrid: structured fact-records + real docs | Fact-records drive deterministic drift detection; real docs preserve context & sourcing |
| **PDF/docx parsing** | liteparse | Fast, reliable extraction without hallucination |
| **Correctness eval** | Answer-key (wrong→right + score) | Objective measure of drift repair; narrate 3–4 flips as evidence |
| **Backbone** | Cognee Cloud (LLM + hosting) | Centralized judge, no local infra, fast prototyping |
| **API strategy** | Brief API directly, no adapter | Simpler, fewer abstraction layers, faster iteration |
| **Judge LLM** | Cloud-native (Cognee improve/cognify) | Handles escalation cases; uses uuid-suffixed throwaway datasets to dodge 409 conflicts |
| **Clients** | Both BauStein + Vitalis ingested | Demonstrate cross-client firewall via per-client datasets; show realistic multi-tenant scenario |
| **Session tiers** | Two-tier shown lightly | Avoid cognitive overhead; focus on core drift logic |
| **Self-improvement** | Two loops: drift router + cognee native skills | Deterministic drift router handles headline cases; cloud skills loop handles grey-band & proposals |
| **Access control** | OFF (`ENABLE_BACKEND_ACCESS_CONTROL=false`) | Simplify cloud integration for hackathon; security hardened post-demo |

---

## Verified API Facts (Live Tonight)

### CloudClient Entry Point
```python
client = cognee.serve(url, api_key)
# Returns CloudClient with methods:
# - remember(content_type, dataset_name, session_id, ..., self_improvement=True, skill_improvement=None, node_set=None)
# - recall(datasets=[...], ...) → list[dict] with answer in ["text"]
# - search(query, datasets=[...], ...)
# - forget(dataset_name=..., everything=True) ← ⚠️ See Known Risks
# - improve(dataset=...)
# - cognify(...)
# - add(...)
# - close()
```

### Dataset Scoping (Cross-Client Firewall)
- `recall()` filters by `datasets=[...]` parameter
- Each client gets a dedicated dataset name (e.g., `baustein`, `vitalis`)
- Dataset scoping is the enforcement mechanism; no row-level ACL needed

### remember() Signature & Behavior
- **Kwargs:** `dataset_name`, `session_id`, `self_improvement` (default `True`), `content_type`, `skill_improvement`, `node_set`
- **Drift control path:** Pass `self_improvement=False` to skip native cloud auto-improve (we control drift in our deterministic router)
- **Skills loop:** `skill_improvement` payload shape TBD — confirmed via grep in Task 9 Step 1 before coding

### recall() Returns & Scoping
- Returns `list[dict]` with answer in `answer["text"]`
- Scope via `datasets=[...]` to enforce per-client isolation
- Coarse forget (see below) means we rely on re-`remember`ing winners so recall favors them

### Forget: Coarse & Flaky
- **Bug:** `client.forget(everything=True)` throws cloud-side 500 on DELETE endpoint
- **Mitigation:** Project-wide `config.safe_forget(client, **kw)` wraps forget as best-effort (never crashes callers)
- **Demo strategy:** Never delete losers; instead, re-`remember` winners with higher trust so recall favors them
- **409 avoidance:** LLM judge uses uuid-suffixed throwaway datasets (e.g., `baustein-judge-abc123`) to dodge conflicts from stale undeleted datasets

### Drift Router (Deterministic)
Resolves headline cases without LLM:
- **Trust + recency override:** High-trust recent fact beats old low-trust
- **Hard-fact HOLD vs low-trust source:** Keep fact if sourced; quarantine unsourced claims
- **Multivalue = keep-both:** Contradiction stays contradiction (not a bug)
- **Age-ratio staleness:** Fact X is stale if age(X) > 2×age(most-recent-similar)
- **Value-equality redundancy:** Same value, same source, same dataset = one record
- **Unsourced quarantine:** Fact with source=null lands in PARK_UNSOURCED

### Judge LLM (Escalation Only, Cloud)
- Handles grey-band cases (conflicting sources, partial staleness, unclear multivalue)
- **PARK when unsure:** Safe fallback; never overwrite with low-confidence
- Called via `recall()` + cloud cognify/improve; uses uuid-suffixed dataset names
- Verbosity: guard with `startswith("YES") or startswith("NO")` + PARK fallback

---

## Architecture Summary

```
Ingest Layer (Task 1,7)
  ↓ (real docs + structured facts)
Fact Store (JSONL + Cognee datasets)
  ↓
Lint Engine (Tasks 2–5, 8)
  ├─ Drift Router (deterministic: resolve T+R, staleness, redundancy, unsourced)
  └─ Judge Escalation (cloud LLM: grey-band, verbosity guard, PARK on unsure)
  ↓
Receipt Writer (Task 5,8)
  └─ Immutable decision log (decisions.jsonl + decisions.md)
  ↓
Query Loop (Task 6 + native skills loop Task 9)
  ├─ Before: WRONG/STALE answers
  └─ After: RIGHT answers (drift fixed)
  ↓
Demo (Task 10)
  └─ Show: clashes N→0, receipt path, 3–4 flips
```

**Self-Improvement Loops:**
1. **Our drift router** (Tasks 2–8): Deterministic fact-level repair, every action logged
2. **Cognee native skills loop** (Task 9): Cloud proposals, filtered via judge, applied with uuid-suffixed throwaway datasets

---

## Known Runtime Risks

### 1. `forget()` Returns 500 on Cloud Side
- **Symptom:** `client.forget(everything=True)` or `client.forget(dataset_name=...)` crashes with 500
- **Root:** DELETE endpoint is flaky
- **Mitigation:** `config.safe_forget(client, **kw)` wraps as best-effort; demo never crashes
- **Demo consequence:** We don't delete losers; we re-`remember` winners to bias recall

### 2. Dataset Cleanup (409 Conflict)
- **Symptom:** Repeated calls with same dataset name may 409 if prior forget didn't complete
- **Mitigation:** Judge uses uuid-suffixed throwaway datasets (`baustein-judge-abc123`)
- **Cleanup:** Acceptable loss for hackathon; post-demo hardening can add tenant-level GC

### 3. Judge Verbosity
- **Symptom:** Cloud improve/cognify may return multi-paragraph explanations instead of YES/NO
- **Mitigation:** Guard with `response.startswith("YES") or startswith("NO")` + PARK fallback
- **Escalation:** If judge is consistently verbose, reduce prompt size or add explicit `max_tokens`

### 4. Skills Loop Payload Shape (Task 9 TBD)
- **What's unconfirmed:** Exact shape of `skill_improvement` dict (apply, reasoning, etc.)
- **How we'll verify:** Task 9 Step 1 greps `skill_improvement` / `improve` in `.venv/.../cognee/api/v1/`
- **Demo impact:** Minimal — skills loop is optional bonus; demo works without it if needed

---

## Implementation Checklist

- [x] Locked decisions documented above
- [x] API facts verified live (remember/recall/forget/judge payload, dataset scoping, coarse forget)
- [x] Deterministic drift router finalized (Tasks 2–5)
- [x] Judge escalation + PARK fallback specified (Task 8)
- [x] Receipt writer ready (Task 5, Task 8)
- [x] Cloud integration tested (remember→recall smoke test passed)
- [x] Demo strategy confirmed (re-remember winners, no delete losers)
- [ ] Skills loop payload verified (Task 9 Step 1 grep)
- [ ] README run instructions written (Task 11 Step 2)
- [ ] Code implementation (Tasks 1–10)
- [ ] Final commit (Task 11 Step 3)

---

**Status:** Design & grill locked. Ready to code. No TBD in critical path.
