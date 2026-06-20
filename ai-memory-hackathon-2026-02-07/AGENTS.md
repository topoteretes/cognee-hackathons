# cognee-qdrant-starter

Hackathon starter repo for the **AI-Memory Hackathon by cognee**. Three FastAPI projects demonstrating semantic search, spend analytics, and anomaly detection on procurement data.

## Stack

- **cognee** — knowledge graph memory (entity extraction, relationships, summaries)
- **Qdrant Cloud** — managed vector DB (14,837 vectors, 768-dim, cosine distance)
- **Distil Labs** — fine-tuned SLM for reasoning (local GGUF or hosted API)
- **DigitalOcean** — deployment platform (App Platform, Spaces for storage)
- **nomic-embed-text** — local embeddings (768-dim, llama-cpp-python)

## Project Structure

```
project1-procurement-search/   # Semantic search UI — port 7777
project2-spend-analytics/      # Spend dashboard — port 5553
project3-anomaly-detective/    # Anomaly detection — port 6971
cognee-pipeline/               # Data ingestion via cognee
shared/                        # Shared LLM and embedding modules
models/                        # Local GGUF models (gitignored)
snapshots/                     # Qdrant collection snapshots (gitignored)
```

Each project has: `app.py` (FastAPI + HTML UI), `pyproject.toml`, `uv.lock`, `.env.example`.

## cognee Usage

cognee is the core knowledge graph framework. Use it to add your own data:

### Add data

```python
import cognee

# Add text
await cognee.add("Invoice INV-001 from TechSupply: 50x laptops at $1200 = $60,000")

# Add files
await cognee.add("/path/to/invoice.pdf")
await cognee.add(["doc1.txt", "doc2.csv", "doc3.pdf"])

# Build knowledge graph (extracts entities, relationships, summaries)
await cognee.cognify()
```

### Search

```python
from cognee.api.v1.search import SearchType

results = await cognee.search(
    query_text="Which vendors supply IT equipment?",
    query_type=SearchType.CHUNKS,
)
```

### Search types

```python
SearchType.CHUNKS              # Raw document chunks
SearchType.SUMMARIES           # Document summaries
SearchType.GRAPH_COMPLETION    # LLM reasoning with graph context
SearchType.RAG_COMPLETION      # Traditional RAG
SearchType.NATURAL_LANGUAGE    # Natural language queries
```

### Reset data

```python
await cognee.prune.prune_data()
await cognee.prune.prune_system(metadata=True)
```

### cognee + Qdrant integration

```python
from cognee_community_vector_adapter_qdrant import register
register()  # Use Qdrant as cognee's vector backend
```

## Qdrant Collections

| Collection | Records | Content |
|---|---|---|
| DocumentChunk_text | 2,000 | Invoice and transaction chunks |
| Entity_name | 8,816 | Products, vendors, SKUs |
| EntityType_name | 8 | Entity type definitions |
| EdgeType_relationship_name | 13 | Relationship types |
| TextDocument_name | 2,000 | Document references |
| TextSummary_text | 2,000 | Document summaries |

## Qdrant Features Used

- **Query API** — basic vector search
- **Prefetch + RRF Fusion** — multi-stage ranking
- **Discovery API** — context-aware search with positive/negative examples
- **Recommend API** — find similar items
- **Group API** — faceted results by payload field
- **Batch Query API** — 50 queries per request for duplicate detection
- **Scroll API** — bulk data extraction
- **Payload indexing** — fast filtering on vendor_id, type, etc.

## Distil Labs Integration

Local GGUF or remote API for LLM reasoning:

```python
from shared.llm import init_llm, get_llm_response

# Local mode (default)
init_llm([(path, "Distil Labs"), (fallback_path, "Qwen3-4B")])

# Remote mode (set LLM_MODE=remote)
# Uses LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME

response = get_llm_response(system_prompt, user_prompt)
```

## DigitalOcean Deployment

```bash
# Upload to DO Spaces
uv run python upload-to-spaces.py

# Deploy to App Platform
doctl apps create --spec .do/app.yaml
```

Set `LLM_MODE=remote` and `EMBED_MODE=remote` for deployed containers.

## Build & Run

```bash
# 1. Set up Qdrant Cloud credentials
cp .env.example .env
# Edit .env with QDRANT_URL and QDRANT_API_KEY

# 2. Restore snapshots (if needed)
uv run python restore-snapshots.py

# 3. Run a project
cd project1-procurement-search
cp .env.example .env
uv sync
uv run python app.py
```

## Environment Variables

| Variable | Description |
|---|---|
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |
| `LLM_MODE` | `local` (GGUF) or `remote` (API) |
| `LLM_API_URL` | OpenAI-compatible endpoint for remote LLM |
| `LLM_API_KEY` | API key for remote LLM |
| `EMBED_MODE` | `local` (GGUF) or `remote` (API) |
| `EMBED_API_URL` | OpenAI-compatible endpoint for remote embeddings |

## Code Patterns

### Embedding a query

```python
from shared.embeddings import init_embeddings, get_embedding

init_embeddings(model_path)
vector = get_embedding("search query")  # Returns 768-dim list
```

### Qdrant search with prefetch

```python
from qdrant_client.models import Prefetch, Query

results = qdrant.query_points(
    collection_name="DocumentChunk_text",
    prefetch=[
        Prefetch(query=vector, using="", limit=50),
    ],
    query=Query(fusion="rrf"),
    limit=10,
)
```

### Qdrant Discovery API

```python
from qdrant_client.models import DiscoverRequest, ContextPair

results = qdrant.discover(
    collection_name="DocumentChunk_text",
    target=query_vector,
    context=[ContextPair(positive=pos_id, negative=neg_id)],
    limit=10,
)
```

## Gotchas

- All collections use 768-dim vectors from nomic-embed-text. Do NOT mix embedding models.
- cognee stores internal state in SQLite. Run `cognee.add()` + `cognee.cognify()` before using `/cognee-search`.
- Each project needs its own `.env` file with Qdrant credentials.
- Never commit `.env`, models, snapshots, or large binaries.

## Data

- 20 vendors (vendor_id 1-20)
- 1,000 invoices + 1,000 transactions
- Products: monitors, laptops, SSDs, RAM, keyboards, HDDs
