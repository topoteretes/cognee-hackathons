# Team Submission

## Team

- Team name: Askvio Wiki Memory
- Participants: Luigi Russo
- Wiki / project name: Askvio Wiki Memory PoC

## Wiki Overview

Askvio Wiki Memory is a hackathon proof-of-concept for ecommerce support knowledge bases. It compares a classic vector-retrieval answer path with an LLM-wiki-style memory that turns uploaded ecommerce HTML into canonical wiki pages, headed sections, fact cards, and entity links. The wiki self-improves when a user rates or corrects an answer: the correction is first stored as session feedback and then promoted into the wiki as a durable fact card, after which linting deduplicates the fact set.

- Domain or data sources: Ecommerce product, policy, FAQ, shipping, returns, warranty, sizing, and landing-page HTML.
- Primary use case: Give customer-support or shopping-assistant answers grounded in a merchant knowledge base, while making answer quality inspectable and improvable.
- What makes it stand out: The app gives side-by-side vector and wiki answers, exposes evidence and KPIs, lets the user inspect generated wiki internals, and demonstrates a concrete self-improvement loop from feedback into new wiki facts.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): One or more uploaded `.html` ecommerce documents, such as policy pages, product pages, FAQs, and support pages.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): FastAPI receives uploads, normalizes the HTML, builds an OpenAI/vector baseline from chunks, builds the wiki from pages/sections/facts/entities, writes session events to Redis, and optionally mirrors distilled pages into Cognee when `ENABLE_COGNEE=1`.
- Code entry point: `POST /api/ingest` in `app/main.py`; HTML parsing in `app/html_processing.py`; vector/wiki construction in `app/retrieval.py`; Redis/Cognee adapters in `app/memory.py`.

### Query + Self-improve

- How users query the wiki: Users ask a question in the browser UI. `POST /api/query` retrieves vector evidence and wiki evidence, asks OpenAI to write final answers from each evidence set when configured, and returns side-by-side answer cards with metrics.
- Where feedback comes from (user rating, agent critic, eval, ...): Human feedback from the UI, including rating and corrected answer text.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting, graph rewrite, ...): `POST /api/feedback` records a Redis `human_feedback` event, promotes the correction to the wiki as a new fact under a `Human Feedback` page, links entities from the question/correction, and runs wiki linting.
- Code entry point: `POST /api/query` and `POST /api/feedback` in `app/main.py`; feedback promotion in `WikiKnowledgeBase.apply_feedback(...)` in `app/retrieval.py`.

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale pruning, ...): Deduplicate fact cards by normalized lowercase fact text so repeated ingest/feedback does not accumulate duplicate facts.
- How it runs (scheduled, on-write, on-demand): On write after ingest/build and after feedback promotion; it is also simple enough to call on demand in code.
- Code entry point: `WikiKnowledgeBase.lint(...)` in `app/retrieval.py`, invoked from `POST /api/ingest` and `POST /api/feedback` in `app/main.py`.

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: `How much would it cost to ship to Italy?`
- Result: The wiki answer missed the country-to-region inference and replied that the cost to ship to Italy was not specified in the available context. It mentioned only international returns and did not map Italy to the UK & Europe shipping region.
- Score (your own metric, judge-readable): 0/1 for factual correctness on the shipping price; the vector baseline won this example because it answered with the UK & Europe rate and additional duty/tax caveat.
- Recorded feedback:

```text
error_type: region_inference_miss
error_message: Wiki did not infer that Italy belongs to the UK & Europe shipping region.
feedback: Shipping to UK & Europe region costs $19.95.
success_score: 0
```

### Improved Run

- Query / task: `How much would it cost to ship to Italy?`
- Result: After using the self-improve function, the wiki answered: `Shipping to Italy, which falls under the UK & Europe region, costs $19.95.`
- Score: 1/1 for core factual correctness on the shipping price and region. It is still less complete than the vector answer because the vector path also mentioned possible customs duties and import taxes.
- What changed in the wiki between runs:

```text
Before:
No fact connected Italy to the UK & Europe shipping-rate rule, so the wiki could not resolve the shipping cost.

After:
A human-feedback fact was promoted into the wiki: "Shipping to UK & Europe region costs $19.95." The wiki then used that improved memory to answer the Italy shipping question correctly.
```

## Example Reply Comparison Results

### Store locations

- Q: `Where are your stores?`
- Vector answer: UrbanWear has flagship physical stores in New York (SoHo), Los Angeles (West Hollywood), and Chicago (Wicker Park). For current store hours and addresses, you can check `urbanwear.com/stores`.
- Wiki answer: Our flagship stores are located in New York (SoHo), Los Angeles (West Hollywood), and Chicago (Wicker Park). For current hours and exact addresses, please check `urbanwear.com/stores`.
- Result: Tie.

### Defective item

- Q: `What happens if I get a defective item?`
- Vector answer: If you receive a defective item from UrbanWear, email `support@urbanwear.com` with your order number and a photo of the defective product. They will cover all return shipping costs and either replace the item or issue a full refund, including the original shipping charges. You need to return the original item and place a new order for a replacement, or they will refund you after inspection. Refunds typically take 5–7 business days to process.
- Wiki answer: If you receive a defective item, UrbanWear will cover all return shipping costs and either replace the item or issue a full refund, including the original shipping charges.
- Result: Vector. The wiki was correct but shorter and less complete.

### Apple Pay and payment methods

- Q: `Can I use Apple Pay to pay for my order? Which other payment methods can I use?`
- Vector answer: Yes, you can use Apple Pay to pay for your order. Other accepted payment methods include Visa, Mastercard, American Express, Discover, PayPal, Google Pay, Shop Pay, and UrbanWear gift cards. Bank transfers, cheques, and cryptocurrency are not accepted.
- Wiki answer: Yes, you can use Apple Pay to pay for your order. Other accepted payment methods include Visa, Mastercard, American Express, Discover, PayPal, Google Pay, Shop Pay, and UrbanWear gift cards.
- Result: Tie. The vector answer includes one extra negative detail, but both answer the asked question.

### Shipping to Italy

- Q: `How much would it cost to ship to Italy?`
- Vector answer: Shipping to Italy, as part of the UK & Europe region, costs $19.95 with a delivery time of 10–14 business days. International orders may be subject to customs duties and import taxes, which are the customer's responsibility.
- Wiki answer before improvement: The cost to ship to Italy is not specified in the available context. It only mentions that international returns must be shipped at your own cost to their Columbus warehouse but does not provide shipping rates for sending orders to Italy.
- Result before improvement: Vector. The wiki missed that Italy belongs to Europe.
- Wiki answer after improvement: Shipping to Italy, which falls under the UK & Europe region, costs $19.95.
- Result after improvement: Wiki becomes correct on the core shipping-cost question, though still less complete than vector because it omits delivery time and duties/taxes.

### Final evaluation comments

The wiki tends to give fast, short replies that are often correct but less complete than their vector equivalents. The shipping-to-Italy example was the clearest miss: the knowledge base contained a UK & Europe shipping rate, but the wiki initially could not resolve that Italy belongs to Europe. The self-improvement loop fixed the core miss by adding the feedback fact `Shipping to UK & Europe region costs $19.95`, after which the wiki produced the correct price.

## Architecture

The core pattern is Redis as hot session memory, distilled into a wiki/Cognee-style permanent memory.

```text
[uploaded ecommerce HTML + agent/user turns]
        |
        v
[FastAPI app]
        |
        +--> [Redis — session memory]
        |        hot per-session events: uploads, build summaries, queries, feedback
        |
        +--> [Vector baseline]
        |        OpenAI embeddings when configured; deterministic term vectors otherwise
        |
        +--> [Wiki memory]
        |        pages, sections, fact cards, entity index, promoted feedback facts
        |
        +--> [Cognee permanent memory — optional]
                 distilled wiki pages mirrored when ENABLE_COGNEE=1
        |
        v
[recall / answer comparison / feedback -> improve -> lint]
```

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Build events, query comparison metrics, human feedback payloads, and feedback-distillation events.
- How and when content is distilled into the graph: Uploaded HTML is distilled during ingest into pages, sections, facts, and entity links. Corrective feedback is distilled immediately by creating a new durable fact on the `Human Feedback` page.
- What stays in Redis vs. what gets promoted: Redis keeps hot per-session event history. Cleaned HTML-derived pages/facts and user corrections are promoted to the wiki memory; optionally, distilled pages are mirrored into Cognee.
- How distillation quality improved between baseline and improved run: The Italy shipping feedback added a general UK & Europe shipping-rate fact, letting a later query map Italy to the correct shipping cost.

## Agents / Skills (if any)

No external skill packs or multi-agent roles are required for the demo. The app itself has three logical roles:

```text
Skill path(s): N/A
Roles:
  - Ingestor: FastAPI upload/build route plus HTML parser
  - Querier: vector/wiki retrieval plus OpenAI answer generation
  - Linter: wiki fact deduplicator
  - Critic: human evaluator through UI feedback
```

## Reproduction

Commands to reproduce the demo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
export OPENAI_API_KEY="sk-..."
docker compose up -d redis
uvicorn app.main:app --reload
```

Open `http://localhost:8000`, upload ecommerce HTML files, click **Build vector + wiki KB**, ask questions, compare answers, and use the self-improve feedback form.

Environment variables required:

```text
OPENAI_API_KEY          # optional but recommended for OpenAI embeddings and answer generation
REDIS_URL               # optional if using redis://localhost:6379/0
ENABLE_COGNEE           # optional; set to 1 to mirror distilled wiki pages into Cognee
LLM_API_KEY             # optional; used by Cognee, can be the same value as OPENAI_API_KEY
OPENAI_CHAT_MODEL       # optional model override, default from app config
OPENAI_EMBEDDING_MODEL  # optional embedding override, text-embedding-3-small by default
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: Run locally with the reproduction commands above and use the browser UI at `http://localhost:8000`.
- 3-minute pitch outline:

```text
1. Problem / idea: ecommerce assistants need grounded answers, but support KBs drift and misses are hard to inspect.
2. Ingest demo: upload UrbanWear/ecommerce HTML and build both vector baseline and wiki memory.
3. Query demo before improvement: ask shipping-to-Italy and show vector wins while wiki misses the Europe inference.
4. Self-improve step: submit feedback: "Shipping to UK & Europe region costs $19.95".
5. Query demo after improvement: ask again and show the wiki now answers the correct Italy shipping price.
6. What is next: richer graph reasoning, conflict linting, scheduled stale-page pruning, and deeper Cognee integration.
```

## Links

- Repo: current repository
- Slides / writeup: N/A
- Anything else: N/A
