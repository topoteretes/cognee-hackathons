# ICP — Sponsor (GTM Tech Week London 2027)

Who we sell sponsorship to, and the "why now" that makes a company worth approaching this quarter.
This is the filter behind `lookalike_features.csv` and the `clay_table_sponsor-prospects.csv` scoring.

## The one-line ICP
A company that **sells to go-to-market operators** (sales, RevOps, demand gen, marketing, CS) — or
services / funds them — **with a field-marketing or events budget** and a reason to be in front of a
UK/EMEA GTM audience right now.

## Three sub-segments (all real in the data)
1. **RevTech / GTM SaaS** — sales intelligence, enrichment, engagement, conversation intelligence,
   enablement, RevOps, CRM, ABM, intent, routing, AI SDRs. The core. (Cognism, Clay, Apollo, Gong,
   Outreach, Pigment, 11x, Common Room, …)
2. **GTM service providers** — agencies and consultancies that sell outbound, demand gen, RevOps and
   GTM-engineering to the same buyer. (Operatix, Sopro, Huble, Transmission, StackOptimise, …)
3. **Investors** — VCs backing B2B SaaS who want logo presence and founder access. (Notion Capital,
   Seedcamp, Dawn, Atomico, Inovo, …)

## Firmographic fit
- **Sells to GTM**: yes (hard gate).
- **UK / London presence**: HQ here > confirmed London office > actively expanding to EMEA. London-HQ
  weights highest — they have the most reason to own a home-market stage.
- **Size**: 11–50 through 1K–5K is the sweet spot (budget exists, decision is fast). 5K+ = enterprise
  cycle, longer. 1–10 = Startup/Community tier only.
- **Stage / capital**: recently funded or profitable-and-growing → events budget exists.

## "Why now" triggers (what `signals_feed.csv` watches)
- **Opened / scaling a London or EMEA office** (the strongest single trigger — see Clay).
- **Raised a round** in the last ~12 months.
- **Hired a Head of Demand Gen / Field Marketing / first EMEA marketer.**
- **Already sponsors GTM events** (Sculpt, SaaStock, Pavilion, RevOps Festival).
- **Leadership posting on AI + GTM** (warm, brand-led, will say yes to a stage).

## Scoring → tier → package
`lookalike_features.csv` scores six dimensions (UK/London presence, sells-to-GTM, recently funded,
events-budget signal, audience overlap, hiring demand gen) into `icp_fit_score` (0–99):
- **A (75+)** → Headline / Platinum. Anchor accounts. Co-create, don't sell a booth (esp. Clay).
- **B (55–74)** → Gold / Silver. The volume of the roster.
- **C (<55)** → Silver / Startup / Side-event. Community tier, fast close.

## Anti-ICP (see `do-not-approach.csv`)
- **Runs a competing event** (Pavilion, SaaStock, HubSpot INBOUND, Dreamforce) → partner or
  cross-promote, do not pitch a sponsorship.
- Already committed budget elsewhere this cycle; flagged-negative accounts.

## What "past_sponsor" means here
The real Warsaw 2026 sponsors (tagged `Past Sponsor` in `attio_companies.csv`) are the warm renewal
list and the lookalike seed — UC2 builds "20 companies like our best sponsors" off them.
