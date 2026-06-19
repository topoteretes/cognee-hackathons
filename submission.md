# Adverra Company Brain — Hackathon Submission

## Team / Project
**Adverra Company Brain** — a self-improving support brain for the (imaginary)
user-acquisition company **Adverra** and its consumer rewarded-earnings product
**Cashly** (a Freecash-style platform).

## The idea
We implement Karpathy's **LLM Wiki** on top of **Cognee** and expose it as a
**Slack support agent**. The agent answers product/support questions from the
wiki, **escalates to a human expert when it doesn't know**, and **learns from
that human's correction** so the same question is answered automatically next
time.

### Karpathy's three layers → our system
| Layer | Implementation |
|---|---|
| Raw sources (immutable) | `raw/` — 5 help-center articles, product pages, FAQ, meeting notes |
| The wiki (LLM-owned, compiled) | Cognee knowledge graph, built by `src/ingest.py` |
| Schema / workflow | `my_skills/` (ingestor, qa-answerer, linter) + Ingest / Query+Improve / Lint |

### Two memory tiers (same Cognee instance)
- **Session memory** — every Slack call passes `session_id = thread_ts`
  (per-conversation working memory).
- **Permanent graph** — verified corrections are remembered without a
  `session_id` (durable, cross-session).

## The self-improvement loop
1. User `@mentions` the bot in Slack.
2. Bot queries the brain (`SearchType.AGENTIC_COMPLETION`, `session_id=thread`)
   and posts its best answer **+ tags the responsible expert** to verify.
3. **👍** → logged as a positive `SkillRunEntry`.
4. **👎 + a threaded reply with the correct answer** →
   - `cognee.remember(correction)` files the fact into the permanent graph
     (the wiki grows), and
   - a `SkillRunEntry` (low score) proposes & applies a `qa-answerer` skill
     rewrite (`src/feedback.py`).
5. Asking the same question again now returns the learned answer.

## Demo evidence
- **Answer from the wiki:** "What is the PayPal withdrawal fee and limits?" →
  correct, source-cited answer (5% fee, $5–$200, 190+ countries, instant/~30min)
  → expert 👍. *(screenshot)*
- **Escalation:** "What is Cashly's referral bonus program?" → "The knowledge
  base contains no information…" → **@tags the expert**. *(screenshot)*
- **Self-improvement:** expert 👎 + posts the correct referral terms → bot
  writes them into the brain → re-asking returns the learned answer.
  *(before/after — see note below)*

> **Note on the live write-back:** the event-provided OpenAI key became
> spend-capped mid-demo (chat-completions returned 401 while embeddings still
> worked), so the final cognify-based write-back couldn't run on the day. The
> code path is complete and runs end-to-end on a healthy key — see
> `src/feedback.py` and the graceful-degradation handling in `src/slack_app.py`.

## Cognee Cloud
`src/push_to_cloud.py` pushes the locally-built brain to a managed Cognee Cloud
instance via `cognee.serve(...)` + `cognee.push(...)` (set `COGNEE_CLOUD_URL` /
`COGNEE_API_KEY`). Runs local-first by design; Cloud push is one command.

## Run it
```bash
uv venv --python python3.13 && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env            # add LLM_API_KEY + Slack tokens
python -m src.ingest            # build the wiki
python -m src.slack_app         # start the Slack agent (Socket Mode)
python -m src.lint              # coherence check
python -m src.push_to_cloud     # optional Cloud bonus
```

## Repo map
- `raw/` — immutable sources · `my_skills/` — skills
- `src/ingest.py` · `src/query.py` · `src/slack_app.py` · `src/feedback.py` ·
  `src/lint.py` · `src/push_to_cloud.py` · `src/brain.py`
