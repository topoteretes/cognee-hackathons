![AI-Memory Hackathon by cognee](hackathon-banner.jpg)

# AI Hack Night

Before you start building, complete the setup below. Once setup is finished, you'll have access to Cognee's search interface, backed by a prebuilt knowledge graph generated from synthetic invoice and transaction data. Your job is to build anything that uses this QA capability in a meaningful way.

## What You Work With

- Query Cognee using natural-language questions (see how `completion` is generated in the `solution_q_and_a.py`).
- Receive structured or free-text answers.
- Use those answers, however, you like in your project.

## Constraints

- Qdrant must be the vector store of choice – whether local or hosted.
- The local model must remain functional; online LLM use is optional.
- The raw data included in the `data` folder is there for reference and should not be used directly.

## What You Can Build

Any tool, workflow, interface, or feature that benefits from QA over vendor, product, payment, or order information.

## Deliverables

- Create a folder named `submission` on your USB stick and place your entire project inside it. Alternatively, you can share your GH repo with [luca@topoteretes.com](mailto:luca@topoteretes.com)
- Your project must include code that demonstrates successful queries to Cognee.
- Be ready to give a short demo.

## Notes

- You do not have to add new files, modify or enrich the graph. In case you want to, there is some additional data in the `optional_data_for_enrichment` folder.

## Setup for Q&A with Qdrant and Local Model

**We will set up**:
- Ollama with two local models (embedding and LLM)
- A Python virtual environment with pinned dependencies
- A Cognee knowledge graph imported from prebuilt data
- A local Qdrant vector store loaded with snapshot data
- The question answering script (`solution_q_and_a.py`)

**This will allow you to**:
- Access ingested data from invoice and transaction documents
- Retrieve structured context from a knowledge graph for LLM queries
- Ask natural-language questions about the data using a local language model
- Build tools, agents, or workflows on top of the Q&A pipeline

**Before installation**:
- copy `models/` from the USB to your working directory
- do the same for `cognee_export/`
- verify the three subdirectories contain Modelfile and a *.gguf each

**Project installation**:
```bash
# Ollama installation
brew install ollama   # Mac OS
ollama serve &

# Ollama model registration
cd models
ollama create nomic-embed-text -f nomic-embed-text/Modelfile
ollama create cognee-distillabs-model-gguf-quantized -f cognee-distillabs-model-gguf-quantized/Modelfile
cd ..

# Initialize python environment, install dependencies
uv venv
source .venv/bin/activate
uv sync

# Graph setup
python setup.py

# Qdrant (local Docker)
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage qdrant/qdrant

# Configure for use locally, retrieve data, restore to database
cp .env.example.local .env
uv run python download-from-spaces.py
uv run python restore-snapshots.py

# Run Q and A example
python solution_q_and_a.py
```

**Pitfalls to avoid**:
- failing to copy both `models/` and `cognee_export/` from USB
- building the venv in `models/` instead of the project root
- having a stale venv activated
- Ollama is not running
- New Qdrant conflicting with old in Docker

**Next steps**:
- look around the code
- play with the queries
- check out the databases
- build something

## Useful setup commands

Skip this reference if setup went smoothly.

**Turn off and remove Qdrant from Docker**

If necessary for recreating:
```bash
docker stop qdrant && docker rm qdrant
docker volume rm qdrant_storage
```

**Mac start/stop ollama**
```bash
brew services start ollama
brew services stop ollama
brew services info ollama
```

**Linux start/stop ollama**
```bash
sudo systemctl start ollama
sudo systemctl stop ollama
sudo systemctl status ollama
```

**Alternate Ollama Installation**
```bash
# Alternate direct option
curl -fsSL https://ollama.com/install.sh | sh
```

## What data do I have?

**After restore**, your cluster contains 14,837 vectors across 6 collections:

| Collection | Records | Content |
|---|---|---|
| DocumentChunk_text | 2,000 | Invoice and transaction chunks |
| Entity_name | 8,816 | Products, vendors, SKUs |
| EntityType_name | 8 | Entity type definitions |
| EdgeType_relationship_name | 13 | Relationship types |
| TextDocument_name | 2,000 | Document references |
| TextSummary_text | 2,000 | Document summaries |

These items are also connected via semantics in your graph DB.

The models included in the `models/` directory:
- **nomic-embed-text** -- 768-dim embeddings, local inference
- **Distil Labs SLM** -- fine-tuned reasoning model, GGUF quantized
- **Qwen3-4B** -- fallback LLM, optional

## Example Project Architecture

Several example projects which one can work off of (if desired, totally optional). These are three ready-to-run FastAPI projects: semantic search, spend analytics, and anomaly detection on procurement data.

**Stack:** [cognee](https://github.com/topoteretes/cognee) (knowledge graph memory) + [Qdrant Cloud](https://cloud.qdrant.io) (vector search) + [Distil Labs](https://www.distillabs.ai/) (LLM reasoning) + [DigitalOcean](https://www.digitalocean.com/) (deployment)

```
Raw documents
    |
    v
cognee.add() + cognee.cognify()     <-- cognee extracts entities, relationships, summaries
    |
    v
Qdrant Cloud (6 collections)        <-- vectors + knowledge graph stored here
    |
    v
FastAPI apps                         <-- search, analytics, anomaly detection
    |
    v
Distil Labs SLM                     <-- LLM reasoning (local GGUF or hosted API)
    |
    v
DigitalOcean App Platform           <-- deployed and shareable
```

## Example projects

Hackathon participants should feel free to build off of these if they wish, or to do something totally different. The three example projects in project1, project2, and project3 directories are each self-contained with their own`pyproject.toml` and dependencies:
```bash
cd project1-procurement-search  # or project2 or project3
uv sync
uv run python app.py
```

**Project 1: Procurement Semantic Search** (port 7777) -- semantic search across all procurement data with interactive UI.

**Qdrant features:** Query API, Prefetch + RRF Fusion, Group API, Discovery API, Recommend API, payload indexing, filtered search

**Endpoints:** `/search`, `/search/grouped`, `/discover`, `/recommend`, `/filter`, `/ask` (RAG Q&A), `/cognee-search`, `/add-knowledge`, `/collections`

**Project 2: Spend Analytics Dashboard** (port 5553) -- interactive analytics dashboard with Chart.js visualizations and semantic search.

**Qdrant features:** Scroll API (bulk extraction), Query API, Group API, payload indexing

**Endpoints:** `/api/analytics`, `/api/search`, `/api/search/grouped`, `/api/insights` (LLM analysis)

**Project 3: Anomaly Detective** (port 6971) -- automated anomaly detection using vector analysis and Qdrant's Batch Query API. Detection methods include amount outliers (z-score), embedding outliers (centroid distance), near-duplicates (similarity > 0.99), and vendor variance.

**Qdrant features:** Batch Query API (50 recommend queries/request), Recommend API, Scroll API with vectors, payload indexing

**Endpoints:** `/api/anomalies`, `/api/search`, `/api/investigate/{point_id}`, `/api/explain/{point_id}` (LLM explanation)

## Using Qdrant Cloud (alternative to local Docker)

If you prefer hosted Qdrant over local Docker, set up a free cluster at [cloud.qdrant.io](https://cloud.qdrant.io) and use `.env.example` instead of `.env.example.local`:
```bash
cp .env.example .env
# Edit .env -- fill in QDRANT_URL and QDRANT_API_KEY with your Cloud values
uv run python download-from-spaces.py
uv run python restore-snapshots.py
```

## Example results

Example results comparing LLM and SLM outputs can be found in `responses.txt`.

## Adding your own data

The starter data was built using cognee's ECL (Extract, Cognify, Load) pipeline:
```bash
cd cognee-pipeline
cp .env.example .env
# Edit .env: add Qdrant credentials + LLM provider
uv sync
uv run python ingest.py
```

Programmatic usage:
```python
import cognee
from cognee.api.v1.search import SearchType

await cognee.add("Your document text here...")
await cognee.cognify()
results = await cognee.search(
    query_text="What vendors supply IT equipment?",
    query_type=SearchType.CHUNKS,
)
```

Supported input types: plain text strings, PDF, DOCX, TXT, CSV files, URLs, and directories of files.

To reset and re-ingest from scratch:
```python
await cognee.prune.prune_data()
await cognee.prune.prune_system(metadata=True)
```

See [cognee docs](https://docs.cognee.ai) for full pipeline options.


## Using Qwen3 as an alternative model

Register the Qwen3 model with Ollama:
```bash
cd models
ollama create Qwen3-4B-Q4_K_M -f Qwen3-4B-Q4_K_M/Modelfile
cd ..
```

Access it via the standard OpenAI-compatible interface at `http://localhost:11434/v1` with model name `Qwen3-4B-Q4_K_M`.


## DigitalOcean deployment

Two modes are available: **local** (GGUF models, default) and **remote** (API-based inference).

**Local dev** runs the Distil Labs SLM via llama-cpp-python (requires 4-8GB RAM):
```bash
# .env: LLM_MODE=local, EMBED_MODE=local (defaults)
uv run python app.py
```

**Remote deployment** to DigitalOcean App Platform:
```bash
uv run python upload-to-spaces.py
# Set LLM_MODE=remote and EMBED_MODE=remote in .env
doctl apps create --spec .do/app.yaml
```

Or run remotely via Docker:
```bash
docker compose up
```

**Environment variables**:

| Variable          | Default           | Description                                 |
| ----------------- | ----------------- | ------------------------------------------- |
| `QDRANT_URL`      | -                 | Qdrant Cloud cluster URL                    |
| `QDRANT_API_KEY`  | -                 | Qdrant Cloud API key                        |
| `LLM_MODE`        | `local`           | `local` (GGUF) or `remote` (API)            |
| `LLM_API_URL`     | -                 | OpenAI-compatible chat completions endpoint |
| `LLM_API_KEY`     | -                 | API key for remote LLM                      |
| `LLM_MODEL_NAME`  | `distil-labs-slm` | Model name for remote LLM                   |
| `EMBED_MODE`      | `local`           | `local` (GGUF) or `remote` (API)            |
| `EMBED_API_URL`   | -                 | OpenAI-compatible embeddings endpoint       |
| `EMBED_API_KEY`   | -                 | API key for remote embeddings               |
| `SPACES_ENDPOINT` | -                 | DO Spaces endpoint                          |
| `SPACES_BUCKET`   | -                 | DO Spaces bucket name                       |


## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Ollama](https://ollama.com/)
- Docker (for local Qdrant)


## Useful commands
