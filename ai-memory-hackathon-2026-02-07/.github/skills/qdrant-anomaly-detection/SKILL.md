---
name: qdrant-anomaly-detection
description: Detect anomalies in procurement data using Qdrant vector operations. Covers centroid-based outlier detection, near-duplicate finding via batch recommend, amount z-score analysis, and vendor variance scoring. Use when building anomaly detection, fraud detection, or data quality features.
metadata:
  author: cognee-hackathon
  version: "1.0"
---

# Qdrant Anomaly Detection Patterns

Patterns for detecting anomalies, duplicates, and outliers using Qdrant's vector operations.

## Centroid-Based Outlier Detection

Extract all vectors, compute centroid, flag distant points:

```python
import numpy as np

# Get all vectors via scroll
records, _ = client.scroll(
    collection_name="DocumentChunk_text",
    limit=100,
    with_vectors=True,
    with_payload=True,
)

vectors = np.array([r.vector for r in records])
centroid = vectors.mean(axis=0)

# Cosine distance from centroid
from numpy.linalg import norm
distances = [1 - np.dot(v, centroid) / (norm(v) * norm(centroid)) for v in vectors]

# Z-score flagging
mean_dist = np.mean(distances)
std_dist = np.std(distances)
outliers = [
    (records[i], distances[i])
    for i in range(len(records))
    if (distances[i] - mean_dist) / std_dist > 2.0
]
```

## Near-Duplicate Detection via Batch Recommend

Find duplicates using batch queries with BEST_SCORE:

```python
# Build batch recommend requests for each point
requests = [
    models.QueryRequest(
        query=models.RecommendInput(positive=[record.id]),
        limit=5,
        score_threshold=0.99,  # near-duplicate threshold
    )
    for record in records[:50]  # batch of 50
]

results = client.query_batch_points(
    collection_name="DocumentChunk_text",
    requests=requests,
)

duplicates = []
for i, batch_result in enumerate(results):
    for hit in batch_result.points:
        if hit.id != records[i].id and hit.score > 0.99:
            duplicates.append((records[i].id, hit.id, hit.score))
```

## Amount Outlier Detection (Z-Score)

Flag transactions with unusually high or low amounts:

```python
amounts = [float(r.payload.get("amount", 0)) for r in records]
mean_amt = np.mean(amounts)
std_amt = np.std(amounts)

amount_outliers = [
    (records[i], amounts[i])
    for i in range(len(records))
    if abs(amounts[i] - mean_amt) / std_amt > 2.5
]
```

## Vendor Variance Scoring

Flag vendors with inconsistent pricing:

```python
from collections import defaultdict

vendor_amounts = defaultdict(list)
for r in records:
    vendor = r.payload.get("vendor_name", "Unknown")
    amount = float(r.payload.get("amount", 0))
    vendor_amounts[vendor].append(amount)

high_variance_vendors = [
    (vendor, np.std(amounts) / np.mean(amounts))  # coefficient of variation
    for vendor, amounts in vendor_amounts.items()
    if len(amounts) > 2 and np.mean(amounts) > 0
    and np.std(amounts) / np.mean(amounts) > 0.8
]
```

## Investigate a Flagged Point

Use recommend to find similar records to a flagged anomaly:

```python
similar = client.recommend(
    collection_name="DocumentChunk_text",
    positive=[flagged_point_id],
    limit=10,
    strategy=models.RecommendStrategy.BEST_SCORE,
    with_payload=True,
)
```

## Decision Table

| Anomaly Type | Method | Threshold |
|---|---|---|
| Embedding outlier | Cosine distance from centroid | z-score > 2.0 |
| Amount outlier | Amount z-score | z-score > 2.5 |
| Near-duplicate | Batch recommend similarity | score > 0.99 |
| Vendor inconsistency | Coefficient of variation | CV > 0.8 |
