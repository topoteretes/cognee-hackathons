# Cognee Pipeline Examples

Two deployment options for the cognee procurement search demo.

## Options

| Setup | Vector DB | Embeddings | LLM | API Keys Needed |
|-------|-----------|------------|-----|-----------------|
| [Local](./local/) | Docker (Qdrant) | Ollama | Ollama | None |
| [Cloud](./cloud/) | Qdrant Cloud | Ollama | OpenAI | Qdrant, OpenAI |

## Quick Comparison

### Local (No APIs)
- Everything runs on your machine
- Download pre-built vectors from DO Spaces
- Best for: development, demos, offline use

### Cloud (Managed)
- Vectors in Qdrant Cloud (free tier: 1GB)
- LLM via OpenAI
- Best for: production, team access

## Data Included

Both setups use the same pre-embedded procurement data:
- 2,000 invoices
- 2,000 transactions
- 2,000 vendors
- 8,816 entities
- 14,837 total vectors

## Deployment

See `deploy/` folder:
- `do-app-spec.yaml` - DigitalOcean App Platform
- `digitalocean-droplet.md` - GPU Droplet setup
- `digitalocean-spaces.md` - Host vector snapshots
