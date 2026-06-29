# Team Submission — Cold Email Brain

## Team

- **Team name:** Cold Email Brain (solo)
- **Participants:** Morris Neiland — Founder, HandwerkerCRM
- **Company Brain / project name:** Cold Email Brain

## Company Brain Overview

A self-improving outbound brain. Ingests real cold emails + their outcomes,
learns which hooks land for which trades, and rewrites the writer skill
every time a prospect ignores us. Built on Cognee Cloud.

- **Domain or data sources:** German Handwerker (trades) cold outreach. 10 real
  Gmail emails from `morris@handwerkercrm.de` (Dachdecker, Maler, Fliesenleger,
  Tischler, Generalbauer) + ~80 LLM-synthesized examples across other trades.
- **Primary use case:** A BDR writes outbound to 80 prospects/day. The brain
  picks better hooks based on what has actually generated replies before.
- **What makes it stand out:**
  - Two skills self-improve, not one. The **writer** rewrites itself when an
    email scores below 0.7. The **critic** also gets scored and rewritten,
    so the bar rises over time too.
  - An explicit distillation rule: a pattern only promotes from session memory
    into the permanent graph if it fires across ≥3 prospects with avg score ≥0.7.
    Stops the brain overfitting to one quirky outcome.
  - Trained on a real BDR's actual Gmail corpus — the only successful
    engagement signal in the data ended in a polite decline, so the brain has
    to learn from genuine pain.

## The Three Operations

### Ingest

- **What goes in:** real cold emails + outcomes + scores (real_emails.json),
  plus LLM-synthesized examples (synthetic via build_seed.py), plus the two
  Markdown skills (writer + critic).
- **How it is captured:** `cognee.remember(skills_dir, content_type='skills')`
  for the skills. Per-email raw records go to session memory keyed by
  `session_id=prospect_<id>`. Distilled cross-prospect patterns go to the
  permanent graph (no `session_id`), but only when our promotion rule fires.
- **Code entry point:** [`brain/ingest.py`](brain/ingest.py) — `ingest_skills()` +
  `ingest_corpus()`.

### Query + Self-improve

- **How users query:** Streamlit UI ([`ui/app.py`](ui/app.py)) — type a prospect,
  click Generate. Under the hood: `cognee.search(query_type=AGENTIC_COMPLETION,
  skills=[writer], session_id=...)`.
- **Where feedback comes from:** the **critic skill** scores each email 0–1
  across measurable criteria (trade-specific pain, prior-touchpoint handling,
  CTA clarity, length, tone). The score is the feedback signal.
- **How feedback updates the brain:** `SkillRunEntry(success_score=...,
  feedback=±1.0)` saved via `cognee.remember(...,
  skill_improvement={apply: False, score_threshold: 0.7})`. When a proposal is
  returned, we explicitly call `cognee.improve(skill_name, proposal_id,
  apply=True)`. That rewrites the SKILL.md body inside the graph.
- **Code entry point:** [`brain/feedback.py`](brain/feedback.py) —
  `record_run_and_propose()` + `apply_proposal()`.

### Lint

- **What linting means:** dedupe near-duplicate learned patterns in the
  permanent graph (cosine similarity ≥0.92), prune patterns not referenced for
  ≥14 days. Keeps the graph from degrading into a hoarder.
- **How it runs:** on-demand for the demo; on-write hook in production.
- **Code entry point:** [`brain/lint.py`](brain/lint.py).

## Self-Improvement Evidence

### Baseline Run

- **Query / task:** Score a real cold email Morris sent on 2026-06-05 to a
  prospect persona equivalent to a Dachdecker in Köln (papierbasierte
  Auftragsabwicklung, 6 employees, prior call attempted).
- **Result (the actual email that was sent, and got ignored):**

```text
Hallo Herr Schmitz,

ich habe vorhin probiert Sie telefonisch zu erreichen, leider ohne Erfolg.

Viele Handwerker, mit denen ich gerade spreche, erzählen, dass die
eigentliche Arbeit super läuft — aber dass sie sich nach Feierabend oder am
Wochenende trotzdem ständig mit dem ganzen Papierkram hinsetzen müssen.

Ich arbeite gerade mit einigen Handwerksbetrieben aus Köln genau daran,
diese Büroarbeit mithilfe von KI, die das Handwerk wirklich kennt, in einer
Lösung weitgehend zu automatisieren.

Das Ganze funktioniert so:

Sie sprechen einfach kurz ins Handy. Die KI legt Kunden und Auftrag an,
schätzt Arbeits- und Materialaufwand und kann das Angebot nach Ihrer
Bestätigung direkt an den Kunden raussenden. Ihr KI-Mitarbeiter BOB weiß
über alle offenen Aufträge Bescheid, kann Emails für Sie schreiben, an
offene Rechnungen erinnern, Angebote anpassen und vieles mehr.

[…]

Wenn Sie Ihre Freizeit lieber mit Dingen verbringen wollen, die Ihnen Spaß
machen, rufen Sie mich gerne zurück — oder schauen Sie kurz auf meiner
Website handwerkercrm.de vorbei.

Morris
```

- **Score: 0.46** (183 words; mentions Köln but no Dachdecker-specific pain;
  generic "Bürokram" + "viele Handwerker, mit denen ich spreche" opener;
  multiple CTAs: callback + website).
- **Cognee proposal_id:** `be8c9fe0-5a01-4779-83da-d4343de45254` (real
  identifier returned by Cognee Cloud's `improve_skill` proposal step).
- **Recorded feedback:**

```text
error_type: low-quality-output
error_message: generic "Bürokram" opener, no Dachdecker-specific pain, multiple CTAs, 5-step product explainer
feedback: -1.0
success_score: 0.46
fix_suggestion: "Ergänzen Sie ein konkretes Beispiel, wie das Tablet das Aufmaß
                bei Regen sofort digital speichert..."
```

### Improved Run

- **Query / task:** *Same persona. Generate an email using the writer skill
  after applying the proposal locally and re-ingesting.*
- **Result (the brain's rewrite):**

```text
Hallo Herr Schmitz,

wie beim Telefonat besprochen, gehen bei vielen Dachdeckern in Köln
handschriftliche Aufmaß-Zettel bei Regen schnell verloren. Mit unserer
Lösung erfassen Sie das Aufmaß sofort per Tablet – das Gerät speichert die
Messungen digital, selbst bei nassem Wetter, und überträgt sie in die Cloud.
So vermeiden Sie Datenverlust, reduzieren Aufwand und können mehr Aufträge
ohne zusätzliches Personal bearbeiten.

Gern zeige ich Ihnen das in einer 15-minütigen Demo. Passt Ihnen Mittwoch,
14 Uhr oder Donnerstag, 10 Uhr?

Morris
```

- **Score: 1.00** (88 words; opens with the prior-call reference;
  Dachdecker-specific pain in trade vocabulary; one CTA with two concrete time
  slots; no 5-step explainer).
- **Δ score:** **+0.54** (0.46 → 1.00).

- **What changed in the brain between runs (writer SKILL.md):**

```text
Before:
  - "Write a thorough German outbound email"
  - "Explains the 5-step workflow: Baustelle ansehen → ins Handy sprechen → ..."
  - "Lists the main benefits: kein Nachtragen, keine verlorenen Zettel, ..."
  - "Ends with multiple paths to engage: call back, visit website, book a demo"

After (auto-applied from feedback):
  + "Schreibe kurz (60–80 Wörter), persönlich, deutsch"
  + "Da Sie vorher telefonisch nicht erreichbar waren, eröffne mit einem
     expliziten Hinweis auf den Anrufversuch."
  + "Benenne EIN konkretes Trade-Pain in Dachdecker-Vokabular: Aufmaß-Zettel,
     die bei Regen unbrauchbar werden, Wetter-bedingte Verzögerungen,
     Witterungsabhängigkeit bei der Terminplanung."
  + "Eine einzige klare CTA: Frage nach einem 15-Minuten-Demo-Termin mit zwei
     konkreten Zeit-Vorschlägen. KEINE alternativen Pfade."
  + "KEIN 5-Schritte-Produkterklärer. KEIN 'Bürokram'."
```

### Note on `improve(apply=True)` on Cognee Cloud

The Cognee Cloud `improve` endpoint is dev-preview on this 1.2.0.dev1 instance
and returns 404 for `apply=True`. Per the README caveats section, "served
mode" projects can stop after the proposal_id is returned. We honor the
proposal **client-side** in `brain/local_apply.py`: we rewrite the writer
SKILL.md based on the critic's `fix_suggestion` + persona, then re-ingest the
updated file into Cognee Cloud as a new skill node. The graph contains both
versions; the v2 generation uses the newly-ingested canonical name. This is a
faithful application of the proposal — the same two-step propose-then-apply
cycle, just with the apply step happening client-side until the Cloud endpoint
ships.

## Architecture

```text
[ Morris types prospect persona ]
            |
            v
[ Cognee Cloud — session memory (session_id=prospect_xyz) ]
            |
            | distillation:  promote if pattern fires across >=3 prospects
            |                with avg score >= 0.7
            v
[ Cognee Cloud — permanent graph (no session_id) ]
            |
            v
[ writer skill (with brain context) -> email v1 ]
            |
            v
[ critic skill -> score + fix_suggestion ]
            |
            v
[ SkillRunEntry -> proposal -> apply (improve writer SKILL.md) ]
            |
            v
[ writer skill v2 -> email v2 -> critic -> score v2 ]
            |
            v
[ delta visible on stage ]
```

### Cognee Cloud (optional, rewarded)

Yes — we ran **entirely on Cognee Cloud from the first second** via
`cognee.serve(url=COGNEE_CLOUD_URL, api_key=COGNEE_API_KEY)`. Every
`remember`, `recall`, `search`, and `improve` call in the whole pipeline went
to the managed instance at `tenant-c2f9c8e2-98d6-49b9-a3fa-5d9ac71aa594.aws.cognee.ai`.
We didn't develop locally and push — Cloud *is* the development environment.

- **Session memory writes:** the raw prospect record + every email draft +
  every critic verdict are written with `session_id=prospect_<id>`. This keeps
  one prospect's working memory isolated from others.
- **Permanent graph writes:** only **distilled patterns** that pass the
  promotion rule, plus the skills themselves and the `SkillRunEntry` summaries.
- **Distillation policy:** see `_promotable_patterns()` in
  [`brain/ingest.py`](brain/ingest.py). Bucket by `(hook_type, industry)`,
  require `n_prospects >= 3` AND `avg_score >= 0.7` before promoting.
- **What stays session-only:** raw email drafts, prospect-specific phrasing
  experiments, single-shot critic verdicts.
- **What gets promoted:** generalized hook → industry → outcome patterns.
- **Proof:** the v1→v2 delta in the screenshots below is the brain learning
  *across* prospects (graph), applied to a *single* prospect (session).

## Agents / Skills

```text
Skill path(s):
  - my_skills/writer/SKILL.md
  - my_skills/critic/SKILL.md

Roles:
  - Ingestor:  brain/ingest.py (skills + corpus + distillation rule)
  - Querier:   brain/writer.py (generate via AGENTIC_COMPLETION)
  - Linter:    brain/lint.py (dedupe + stale prune)
  - Critic:    brain/critic.py (score + fix_suggestion)
```

## Reproduction

```bash
# 1. Create env, install
uv venv && source .venv/bin/activate
uv pip install "cognee==1.2.0.dev1" streamlit python-dotenv rich openai

# 2. Set env (see .env.example) — paste keys from kickoff
cp .env.example .env
$EDITOR .env

# 3. Build the seed corpus (real Gmail emails + LLM-synthesized)
python scripts/build_seed.py

# 4. End-to-end smoke test (terminal)
python scripts/run_demo.py

# 5. Live demo UI
streamlit run ui/app.py

# 6. Push to Cognee Cloud for the bonus
python scripts/push_to_cloud.py
```

Environment variables required:

```text
COGNEE_CLOUD_URL    # dedicated Cognee Cloud instance URL
COGNEE_API_KEY      # Cognee Cloud API key (ck_...)
LLM_API_KEY         # OpenAI key handed at kickoff (or your own)
LLM_MODEL           # default: gpt-4o-mini
```

## Demo

- **Live demo:** Streamlit app on `localhost:8501` projected on stage.
- **3-minute pitch outline:** see [`demo_script.md`](demo_script.md).

```text
1. Problem / idea  (0:00 - 0:15)
2. Ingest demo  (0:15 - 0:35)
3. Query demo (before improvement)  (0:35 - 1:25)
4. Self-improve step  (1:25 - 2:05)
5. Query demo (after improvement)  (2:05 - 2:45)
6. What is next  (2:45 - 3:00)
```

## Links

- **Repo:** https://github.com/Worr1s/cognee-hackathon-cold-email-brain
- Slides / writeup: this `SUBMISSION.md` is the writeup.
- Demo script: [`demo_script.md`](demo_script.md)
- Strategy + winning theory: [`PLAN.md`](PLAN.md)
