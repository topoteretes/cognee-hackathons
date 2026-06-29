# BrainFlow Wiki — Lint Report

Generated from `wiki/` · 11 registered findings · **9 open** (need a human).

_Reports only; decisions are never auto-resolved (CLAUDE.md §7)._

## Contradictions — incompatible live claims (6)
- **[A] AI Daily Pick in MVP** — current: **Out of MVP scope** per PRD; PM pulled it in over a recorded Eng scope objection — **unresolved**. Conflicts: PRD §MoSCoW (Won't have) vs Roadmap Q2, Decision Log 2026-05-06, Design Screen 2. _(open)_
- **[C] B2B HR reporting** — current: **Anonymised, aggregated only** (PRD wins; GDPR risk). Conflicts: Sales commitment (per-employee, by name) + Design Screen 6 implement it. _(open)_
- **[E] Launch platform / order** — current: **Simultaneous iOS+Android** per ADR-0001 (persona is Android). Conflicts: Roadmap (iOS-first), GTM (App Store/iOS), Design (iPhone-only shell) contradict it. _(open)_
- **[G] B2C / B2B price** — current: **No source of truth** — pricing has no owner. Conflicts: PRD/OKR imply €4.99/mo; GTM = €3.99/mo; Sales B2B = €22/user/yr (below €25.99 >100-seat tier). _(open)_
- **[H] Exercise length** — current: **Undefined across teams**. Conflicts: PRD = 2–5 min; Content spec = 3–10 min; GTM = 5 min; Design self-contradicts (tiles "2–5 min" vs timer 08:00). _(open)_
- **[K] Category label drift** — current: Same category, two names. Conflicts: Design dashboard tile = "Emotional IQ"; Design radar axis = "Emotional Intelligence". _(open)_

## Superseded but still referenced (2)
- **[B] Paywall timing** — current: **Day 7** (reverted 2026-04-09). Stale refs: Roadmap (Day 3) and Design Screen 5 (Day 3) still cite the superseded value.
- **[F] Backend** — current: **Supabase, EU/Frankfurt** (ADR-0005, GDPR/DiGA). Stale refs: ADR-0002 (Firebase, US) superseded but should be checked for stray references.

## Metric drift — same name, different definition (1)
- **[D] "40% retention" meaning** — PRD = 30-day ≥40%; OKR = 7-day ≥40%; GTM = bare "40% retention".

## Orphans / no owner (4)
- **AI Daily Pick** (Feature) — owner: Accountable Lena Hoffmann (PM); build owner — (none)  ·  wiki/topics/ai-daily-pick.md
- **GDPR Data Protection Impact Assessment (health data)** (OpenQuestion) — owner: (none) — flagged  ·  wiki/topics/gdpr-dpia.md
- **B2B HR dashboard** (Feature) — owner: Accountable Daniela Fuchs (Sales); delivery owner — (TBD)  ·  wiki/topics/hr-dashboard.md
- **Pricing** (Decision) — owner: (none) — flagged  ·  wiki/topics/pricing.md

## Open questions / risks (8)
- **AI Daily Pick** — Disputed — PRD says out of MVP scope; PM pulled it in over an Eng objection  ·  wiki/topics/ai-daily-pick.md
- **Brain Score** — Agreed (Research Finding 2) but not implemented in design  ·  wiki/topics/brain-score.md
- **Training category labels** — Four categories: Focus, Creativity, Emotional IQ, Wellbeing — one label drifts  ·  wiki/topics/category-naming.md
- **Exercise length** — Undefined across teams  ·  wiki/topics/exercise-length.md
- **GDPR Data Protection Impact Assessment (health data)** — Unresolved — no owner  ·  wiki/topics/gdpr-dpia.md
- **B2B HR dashboard** — Anonymised, aggregated usage only (PRD); Sales/Design contradict it  ·  wiki/topics/hr-dashboard.md
- **Pricing** — No source of truth — pricing is unowned  ·  wiki/topics/pricing.md
- **Retention target ("40% retention")** — Undefined — 40% threshold agreed, measurement window is not  ·  wiki/topics/retention-target.md

## Spec-vs-design gaps (2)
- **[I] Ownership gaps** — **No owner** for Pricing, AI Daily Pick build, Health/DiGA; GDPR DPIA open.
- **[J] Brain Score missing from design** — Decision to add a numeric **Brain Score** (Research Finding 2) **not implemented**.
