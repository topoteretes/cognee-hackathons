# Cold Email Brain

> A self-improving outbound brain for German Handwerker cold outreach.
> Built for the [Cognee Cloud Hackathon · Berlin · 2026-06-19](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-cloud-hackathon-2026-06-19).

## What it does

You type a prospect. The brain writes a cold email using patterns learned from
real outbound history. A critic skill scores it. If the score is low, the brain
proposes a rewrite of its own writer skill, applies it, and produces a sharper
v2 — no model retraining, just self-edited instructions.

Two skills both self-improve. Memory is split into a fast per-prospect session
tier and a durable cross-prospect graph, with an explicit promotion rule that
stops the brain from overfitting.

## Quickstart

```bash
uv venv && source .venv/bin/activate
uv pip install "cognee==1.2.0.dev1" streamlit python-dotenv rich openai
cp .env.example .env  # paste the kickoff keys
python scripts/build_seed.py
python scripts/run_demo.py
streamlit run ui/app.py
```

## Layout

```
brain/             Core memory + skill orchestration
  config.py        Env loading + constants
  cognee_client.py serve() wrapper + reset helper
  ingest.py        Two-tier ingest + distillation rule (3 prospects, avg >= 0.7)
  writer.py        Generate email via AGENTIC_COMPLETION + writer skill
  critic.py        Score email + propose fix
  feedback.py      SkillRunEntry -> propose -> apply
  lint.py          Dedupe + prune (3rd required op)
my_skills/
  writer/SKILL.md  Outbound writer (self-improves)
  critic/SKILL.md  Email critic (self-improves)
data/
  real_emails.json 10 real emails from Morris's Gmail
  synthetic.json   LLM-generated (built by scripts/build_seed.py)
  seed.json        Combined
scripts/
  build_seed.py    Generate synthetic + combine into seed.json
  run_demo.py      Full E2E smoke test
  push_to_cloud.py cognee.push for the bonus
ui/
  app.py           Streamlit demo UI
PLAN.md            Strategy + winning theory
demo_script.md     3-minute stage script
SUBMISSION.md      Filled-out submission template
```

## License

MIT
