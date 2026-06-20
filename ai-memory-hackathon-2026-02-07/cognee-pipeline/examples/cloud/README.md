# Cloud Setup (Qdrant Cloud + OpenAI)

Use managed services for production-ready deployment.

## Requirements

- Qdrant Cloud account (free tier available)
- OpenAI API key
- Ollama (local embeddings to match stored vectors)
- Python 3.12+

## Quick Start

```bash
# 1. Copy and edit config
cp .env.example .env
# Edit .env with your API keys

# 2. Install Ollama embedding model
ollama pull nomic-embed-text

# 3. Test it
python demo.py
```

## What's Included

| Component | Where | Model |
|-----------|-------|-------|
| Vector DB | Qdrant Cloud | Managed |
| Embeddings | Local Ollama | nomic-embed-text (768-dim) |
| LLM | OpenAI | gpt-4o |
| Vectors | Pre-loaded | 14,837 in cloud |

## Files

```
cloud/
├── .env.example          # Config template
├── demo.py               # Test script
└── requirements.txt
```

## API Keys Needed

1. **Qdrant Cloud**: https://cloud.qdrant.io
   - Create cluster (free tier: 1GB)
   - Get URL and API key

2. **OpenAI**: https://platform.openai.com
   - Get API key

## Deployment: DigitalOcean App Platform

```bash
doctl apps create --spec deploy/do-app-spec.yaml
```

See `deploy/` folder for full deployment configs.
