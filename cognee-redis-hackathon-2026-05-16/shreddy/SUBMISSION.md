# Team Submission

## Team
- Team name: Shreddy
- Participant: Salim Masmoudi
- Project: Shreddy

## Wiki Overview
Shreddy is an image-first pottery and ceramics price estimation system.  
Users upload an image, the app retrieves visually similar sold lots, proposes an estimated price from comps, and records user feedback (`Yes/No` + optional corrected price) for iterative improvement.

## The Three Operations

### Ingest
- Sold-lot data (image + text + sold price) is ingested and indexed in Elasticsearch.
- Image embeddings are generated and stored in `ceramics_source1_embeddings_v1`.

### Query + Self-improve
- Query modes:
  - Text search
  - Image similarity search (CLIP embedding -> ES vector kNN)
- Feedback loop:
  - User confirms/rejects match quality.
  - Structured feedback is logged to Cognee (`/api/feedback` -> add + cognify).

### Lint
- Dataset deduplication by lot id / URL in ingestion scripts.
- Redis TTL cache keeps query memory fresh and bounded.

## Self-Improvement Evidence
- Baseline: retrieval + median estimate from similar sold items.
- Improvement: explicit user feedback events are persisted with:
  - `image_sha256`
  - `decision`
  - `estimated_price`
  - optional `user_corrected_price`
  - top match IDs and prices
- Result: durable memory is available for future correction-aware pricing behavior.

## Architecture

```text
User Image/Text Query
      |
      v
Web App (Node)
  - /api/search
  - /api/search-image
  - /api/feedback
      |
      +--> Redis (hot cache, short TTL)
      |
      +--> Elasticsearch (search + vector retrieval)
      |
      +--> Cognee (durable feedback memory graph)
```

## Redis-as-session-memory
- Redis caches hot query responses:
  - `/api/search`
  - `/api/search-image`
- Keeps latency low for repeated queries.
- Ephemeral memory stays in Redis; durable human feedback is promoted to Cognee.

## Reproduction
```bash
git clone https://github.com/Masmedeam/shreddy.git
cd shreddy
docker compose up -d
curl -s http://localhost:8787/api/health
```

## Demo
- Live app: http://18.208.252.96
- Loom: https://www.loom.com/share/68faa0ffa65b4063a33da7fec0fbc8af

## Links
- Repository: https://github.com/Masmedeam/shreddy
- Deployment notes: `DEPLOYMENT.md`
