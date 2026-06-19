# Test Examples — Company Brain (BauStein + Vitalis)

Each test: a query + the WRONG answer the brain gives before cleanup + the RIGHT answer after + which drift case + router path it exercises.

## A. Headline demo queries (wrong-before / right-after)

| # | Query | Wrong (before cleanup) | Right (after cleanup) | Drift case | Router path |
|---|-------|------------------------|------------------------|-----------|-------------|
| A1 | "Where can we store BauStein's raw helmet-cam video?" | US-east bucket, faces visible (bau-03) | Anonymized, EU-Frankfurt only, per DPA (bau-02) | stakes-override | judge (hard fact held) |
| A2 | "Which LLM does RFI Copilot run on today?" | GPT-4o (bau-04) | Claude Sonnet 4.5, GPT-4o fallback (bau-05) | contradiction | heuristic (clean override) |
| A3 | "Which LLM powers Vitalis Scribe Assist, and where can it run?" | GPT-4o on consumer OpenAI API (hlth-05 + hlth-03) | Claude, only in HIPAA Azure US-East under BAA (hlth-04 + hlth-02) | contradiction + stakes-override | judge |
| A4 | "What's the AuthFlow integration standard?" | (looks like FHIR vs HL7 v2 conflict) | Both — FHIR R4 outbound, HL7 v2 inbound; complementary (hlth-06 + hlth-07) | fake-contradiction | judge (resolves as no-conflict) |

## B. Router-path coverage (one test per outcome)

| # | Query / trigger | Expected outcome | Path |
|---|-----------------|------------------|------|
| B1 | dedupe "ProgressAI completion %" facts (bau-06 / bau-07) | merge to one, both sources kept | heuristic (sim > 0.92) |
| B2 | "Is BauStein using Pinecone or PostGIS?" (bau-08 / bau-09) | keep both — PostGIS is GIS, not a vector store | judge (fake-conflict) |
| B3 | "What was the SiteGuard pilot scope?" (bau-10, Q2 2024) | retire as stale, flag superseded | heuristic (age > 2x horizon) |
| B4 | "What's the BauStein budget?" (bau-11, source=none) | serve but flag borderline-stale + no-source | heuristic + quarantine-lite |
| B5 | EU PII region conflict (firm-08 / firm-09) — if firm facts loaded | quarantine, NEEDS HUMAN | nobody-sure → park |

## C. Safety / "never silently forget" assertions

| # | Assertion | Check |
|---|-----------|-------|
| C1 | No hard fact (contract/BAA/policy) ever deleted without a receipt | every `hard=true` drop has a receipt line + reason |
| C2 | Casual Slack never silently overrides a hard policy | bau-03, hlth-03 must be FLAGGED, not applied |
| C3 | Every cleanup action produces exactly one receipt line | `len(receipts) == len(actions)` |
| C4 | Quarantined facts are NOT served as truth | bau-11, hlth-05, firm-09 demoted in answers |
| C5 | Cross-client SOW (EUR 480k BauStein vs USD 480k Vitalis) NOT merged | scoped by dataset/node_set per client |

## D. Self-improvement metric (the demo number)

- Seed BauStein (or Vitalis) → run lint cycle → record:
  - `clashes_before` → `clashes_after` (target N → 0)
  - `resolved_free` (heuristic) / `needed_judge` (LLM) / `parked` (human)
  - `health = 1 / (1 + Σ drift_debt)` trending up
- Re-ask A1–A3 after cleanup → answers flip from wrong to right. That flip IS the proof.
