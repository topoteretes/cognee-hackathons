---
name: qdrant-search
description: Semantic search over Qdrant Cloud collections using the Python client. Covers vector search, filtered search, prefetch+RRF fusion, group API, recommend API, discovery API, batch queries, scroll, and payload indexing. Use when building search features, adding new query types, or working with qdrant-client.
metadata:
  author: cognee-hackathon
  version: "1.0"
---

# Qdrant Search Patterns

All projects use `qdrant-client` with 768-dim vectors from nomic-embed-text.

## Client Setup

```python
import os
from qdrant_client import QdrantClient, models

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
```

## Vector Search (Query API)

```python
results = client.query_points(
    collection_name="DocumentChunk_text",
    query=embedding_vector,  # list[float], 768-dim
    limit=10,
    with_payload=True,
)
for point in results.points:
    print(point.id, point.score, point.payload)
```

## Filtered Search

```python
results = client.query_points(
    collection_name="DocumentChunk_text",
    query=embedding_vector,
    query_filter=models.Filter(
        must=[
            models.FieldCondition(
                key="vendor",
                match=models.MatchValue(value="Acme"),
            )
        ]
    ),
    limit=10,
)
```

## Prefetch + RRF Fusion

Multi-stage retrieval combining multiple query vectors:

```python
results = client.query_points(
    collection_name="DocumentChunk_text",
    prefetch=[
        models.Prefetch(query=vector_a, limit=20),
        models.Prefetch(query=vector_b, limit=20),
    ],
    query=models.FusionQuery(fusion=models.Fusion.RRF),
    limit=10,
)
```

## Group API

Group results by a payload field:

```python
results = client.query_points_groups(
    collection_name="DocumentChunk_text",
    query=embedding_vector,
    group_by="vendor",
    limit=5,
    group_size=3,
)
```

## Recommend API

Find similar items by point IDs:

```python
results = client.recommend(
    collection_name="DocumentChunk_text",
    positive=[point_id_1, point_id_2],
    negative=[point_id_3],
    limit=10,
    strategy=models.RecommendStrategy.BEST_SCORE,
)
```

## Discovery API

Guided exploration with context pairs:

```python
results = client.discover(
    collection_name="DocumentChunk_text",
    target=point_id,
    context=[
        models.ContextPair(positive=pos_id, negative=neg_id),
    ],
    limit=10,
)
```

## Batch Query API

Multiple queries in a single request:

```python
results = client.query_batch_points(
    collection_name="DocumentChunk_text",
    requests=[
        models.QueryRequest(query=vector_1, limit=5),
        models.QueryRequest(query=vector_2, limit=5),
    ],
)
```

## Scroll API

Bulk retrieval without ranking:

```python
records, next_offset = client.scroll(
    collection_name="DocumentChunk_text",
    limit=100,
    with_payload=True,
    with_vectors=True,
)
# Paginate with offset=next_offset
```

## Payload Indexing

Create indexes for fast filtering:

```python
client.create_payload_index(
    collection_name="DocumentChunk_text",
    field_name="vendor",
    field_schema=models.PayloadSchemaType.KEYWORD,
)

# Full-text index
client.create_payload_index(
    collection_name="DocumentChunk_text",
    field_name="text",
    field_schema=models.TextIndexParams(
        type="text",
        tokenizer=models.TokenizerType.WORD,
        min_token_len=2,
        max_token_len=15,
        lowercase=True,
    ),
)
```

## Cloud Inference (server-side embeddings)

No local model needed — Qdrant embeds on the server:

```python
from qdrant_client.http.models import Document

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, cloud_inference=True)

results = client.query_points(
    collection_name="my_collection",
    query=Document(text="search query", model="Qdrant/Qwen/Qwen3-Embedding-0.6B"),
    limit=10,
)
```

**Warning:** Cloud inference uses a different embedding model. Existing collections use 768-dim nomic-embed-text vectors — you cannot mix models in the same collection without re-embedding all data.
