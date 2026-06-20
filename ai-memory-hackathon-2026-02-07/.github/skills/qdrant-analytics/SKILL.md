---
name: qdrant-analytics
description: Build spend analytics and dashboards from Qdrant vector data. Covers bulk scroll extraction, aggregation patterns, vendor grouping, and Chart.js visualization. Use when building analytics features, aggregating procurement data, or creating dashboards.
metadata:
  author: cognee-hackathon
  version: "1.0"
---

# Qdrant Analytics Patterns

Patterns for extracting and aggregating data from Qdrant collections for analytics dashboards.

## Bulk Data Extraction via Scroll

Iterate all records for aggregation:

```python
all_records = []
next_offset = None

while True:
    records, next_offset = client.scroll(
        collection_name="DocumentChunk_text",
        limit=100,
        offset=next_offset,
        with_payload=True,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_type",
                    match=models.MatchValue(value="invoice"),
                )
            ]
        ),
    )
    all_records.extend(records)
    if next_offset is None:
        break
```

## Vendor-Grouped Search

Group search results by vendor for comparison:

```python
results = client.query_points_groups(
    collection_name="DocumentChunk_text",
    query=embedding_vector,
    group_by="vendor_name",
    limit=10,      # number of groups
    group_size=5,   # results per group
)

for group in results.groups:
    vendor = group.id
    hits = group.hits
```

## Aggregation Pattern

Extract payloads and aggregate in Python:

```python
from collections import defaultdict

vendor_spend = defaultdict(float)
for record in all_records:
    payload = record.payload
    vendor = payload.get("vendor_name", "Unknown")
    amount = float(payload.get("amount", 0))
    vendor_spend[vendor] += amount

# Sort by spend
top_vendors = sorted(vendor_spend.items(), key=lambda x: x[1], reverse=True)
```

## FastAPI Analytics Endpoint

Return aggregated data as JSON for Chart.js:

```python
@app.get("/api/analytics")
async def analytics():
    records = scroll_all_records("DocumentChunk_text", doc_type="invoice")
    return {
        "total_spend": sum(r.payload.get("amount", 0) for r in records),
        "invoice_count": len(records),
        "by_vendor": aggregate_by_field(records, "vendor_name", "amount"),
        "by_month": aggregate_by_field(records, "month", "amount"),
    }
```

## Decision Table

| Need | Pattern |
|---|---|
| Total spend across all invoices | Scroll all + sum amounts |
| Top vendors by spend | Scroll + groupby vendor + sort |
| Monthly trends | Scroll + groupby month + sort by date |
| Semantic search within analytics | Query API + filters |
| Vendor-grouped search results | Group API with group_by="vendor_name" |
