# Local Setup (No Cloud APIs)

Run everything locally with Docker. No API keys required.

## Requirements

- Docker & Docker Compose
- Ollama (for embeddings + LLM)
- Python 3.12+

## Quick Start

```bash
# 1. Start local Qdrant
docker compose up -d

# 2. Install Ollama models
ollama pull nomic-embed-text
ollama pull qwen3:4b

# 3. Download and restore vector snapshots
cp .env.example .env
python restore_snapshots.py

# 4. Test it
python demo.py
```

## What's Included

| Component | Where | Model |
|-----------|-------|-------|
| Vector DB | Local Docker | Qdrant |
| Embeddings | Local Ollama | nomic-embed-text (768-dim) |
| LLM | Local Ollama | qwen3:4b |
| Vectors | Downloaded snapshot | 14,837 pre-embedded |

## Files

```
local/
├── docker-compose.yml    # Local Qdrant
├── .env.example          # Config template
├── restore_snapshots.py  # Download vectors from DO Spaces
├── demo.py               # Test script
└── requirements.txt
```

## Deployment: DigitalOcean Droplet

For GPU inference on a Droplet:

```bash
# See deploy/digitalocean-droplet.md
```
