# Intro to Cognee — hands-on tutorial

A guided notebook that builds a small "company brain" from the sample Slack
threads and Granola note in this repo, introducing one Cognee concept at a time:

1. **Load data + build graph** — `cognee.remember()` (the Cognee 1.x call that
   replaces `add()` + `cognify()`)
2. **Recall** — `cognee.recall()` for natural-language answers
3. **Node sets** — tag at `remember()`, filter at `recall()` with `scope=[...]`
4. **Custom graph model** — typed `DataPoint` schema + `custom_prompt`
5. **Improve** — `cognee.improve()` + `self_improvement` make the graph sharper
   over time
6. **Add another source** — Granola notes join the same graph

`remember()` rolls ingestion, graph-building, and a self-improvement pass into
one call; you only drop down to `cognee.add()` + `cognee.cognify()` when you want
to decouple ingestion from graph-building (the notebook explains when).

Each section has a short intro and a runnable cell. The final recall question
spans both sources — the bug is reported in Slack and resolved in the Granola
note — which is the whole point of a unified graph.

## Run it

**One command** (needs [uv](https://docs.astral.sh/uv/)):

```bash
bash tutorial/setup.sh
```

This creates `.venv`, installs the tutorial dependencies (`uv pip install -e
".[tutorial]"`), and copies `.env.example` → `.env`. Then add your key to `.env`:

```
LLM_API_KEY=sk-...        # an OpenAI key works
```

And launch:

```bash
source .venv/bin/activate && jupyter lab tutorial/intro_to_cognee.ipynb
```

<details>
<summary>Manual setup (no script)</summary>

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[tutorial]"
cp .env.example .env          # then set LLM_API_KEY
jupyter lab tutorial/intro_to_cognee.ipynb
```
</details>

The notebook runs Cognee **in-process** (local SQLite + LanceDB) — no server,
no Docker required. `LLM_API_KEY` is the only variable it needs; the other
`.env` entries are for the production Slack/Granola pipeline.

## From tutorial to product

Once the concepts click, `src/gtm_brain/` shows the production version:
live Slack/Granola ingestion, an LLM classifier that auto-tags threads, and a
Slack bot that answers from the graph.
