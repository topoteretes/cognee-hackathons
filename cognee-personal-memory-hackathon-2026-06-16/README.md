# cognee-personal-memory

A **personal** memory / life-assistant brain on Cognee — the individual
counterpart to the [company-brain hackathon](../cognee-companybrain-hackathon-2026-06-16).
Ingest your own scattered context (personal Slack, email, Granola notes) into a
single Cognee knowledge graph and ask it things like *"what do I still need to
respond to today?"*.

## 🚀 Start here

**Tutorial — `tutorial/personal_memory_life_assistant.ipynb`.** Builds a small
personal memory graph from the sample data in `sample_data/personal_memory/`
(emails + personal Slack across finance, health, family, travel, …) and walks
through the core loop: ingest → recall → feedback. Runs in-process (no server)
and only needs `cognee`.

```bash
bash setup.sh                 # creates .venv, installs tutorial deps
export LLM_API_KEY=sk-...      # an OpenAI key works
source .venv/bin/activate && jupyter lab tutorial/personal_memory_life_assistant.ipynb
```

No code? Open `personal_assistant_brain_graph.html` in a browser to see an
example of the resulting graph.

## What's here

- `tutorial/personal_memory_life_assistant.ipynb` — the hands-on tutorial
  (plus an `.executed.ipynb` with outputs).
- `sample_data/personal_memory/` — sample personal emails + Slack messages.
- `templates/personal_assistant_brain/` — a runnable scaffold that ingests
  Slack / email / Granola into a personal Cognee graph via **dlt**, then queries
  and visualizes it. See its own `README.md` and `IMPLEMENTATION_PLAN.md`.
- `src/company_brain/` — a **vendored subset** (`normalize`, `schema`,
  `cognee_client`) copied from the company-brain hackathon so this folder runs
  standalone. The template imports these as a small library.

## Running the ingestion template

```bash
uv pip install -e ".[personal-assistant]"
export LLM_API_KEY=...
export COGNEE_DATASET=personal_assistant_brain

python templates/personal_assistant_brain/personal_assistant_brain.py ingest
python templates/personal_assistant_brain/personal_assistant_brain.py ask \
  "What do I still need to respond to today?"
python templates/personal_assistant_brain/personal_assistant_brain.py visualize \
  --output personal_assistant_brain_graph.html
```

See `templates/personal_assistant_brain/README.md` for the full environment
variable reference (Slack / email / Granola) and current status.

## License

Apache 2.0 — see [LICENSE](LICENSE). (Same license as
[cognee](https://github.com/topoteretes/cognee).)
