"""
Project 1: Procurement Semantic Search
FastAPI app with local nomic-embed-text embeddings + Qdrant advanced features:
- Prefetch + Fusion (RRF) — multi-stage retrieval pipeline
- Discovery API — context-aware search with positive/negative examples
- Recommend API — positive/negative point-based recommendations
- Group API — faceted results by type
- Payload-indexed filtering
"""

import os
import sys
import json
import time
from contextlib import asynccontextmanager

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    Prefetch,
    Fusion,
    FusionQuery,
    DiscoverQuery,
    DiscoverInput,
    ContextPair,
    RecommendQuery,
    RecommendInput,
    RecommendStrategy,
)

load_dotenv()

# Add shared module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm import init_llm, get_llm_response, get_model_name, is_available as llm_available
from shared.embeddings import init_embeddings, get_embedding

EMBED_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "models",
    "nomic-embed-text",
    "nomic-embed-text-v1.5.f16.gguf",
)

qdrant = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"],
)

LLM_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "cognee-distillabs-model-gguf-quantized", "model-quantized.gguf"
)
LLM_FALLBACK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "Qwen3-4B-Q4_K_M", "Qwen3-4B-Q4_K_M.gguf"
)

# cognee integration (optional, graceful fallback if not installed)
cognee_available = False
try:
    import cognee
    from cognee.api.v1.search import SearchType
    cognee_available = True
except ImportError:
    pass

COLLECTIONS = [
    "DocumentChunk_text",
    "Entity_name",
    "EntityType_name",
    "EdgeType_relationship_name",
    "TextDocument_name",
    "TextSummary_text",
]


def setup_payload_indexes():
    """Create payload indexes for fast filtering on key fields."""
    for collection in COLLECTIONS:
        try:
            qdrant.create_payload_index(
                collection_name=collection,
                field_name="type",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass
        try:
            qdrant.create_payload_index(
                collection_name=collection,
                field_name="text",
                field_schema=PayloadSchemaType.TEXT,
            )
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_embeddings(EMBED_MODEL_PATH)
    init_llm([(LLM_MODEL_PATH, "Distil Labs"), (LLM_FALLBACK_PATH, "Qwen3-4B")])

    for c in COLLECTIONS:
        info = qdrant.get_collection(c)
        print(f"  {c}: {info.points_count} points")

    print("Setting up payload indexes...")
    setup_payload_indexes()

    if cognee_available:
        try:
            from cognee_community_vector_adapter_qdrant import register
            print("cognee initialized with Qdrant backend.")
        except ImportError:
            print("cognee available but Qdrant adapter not installed.")
    else:
        print("cognee not installed. /cognee-search and /add-knowledge endpoints disabled.")

    print("Ready.")
    yield


app = FastAPI(title="Procurement Semantic Search", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html><head><title>Procurement Search</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e0e0e0; padding: 2rem; max-width: 1200px; margin: 0 auto; }
        h1 { color: #7c3aed; margin-bottom: 0.25rem; }
        .subtitle { color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem; }
        .badge.local { background: #065f46; color: #6ee7b7; }
        .badge.qdrant { background: #1e1b4b; color: #a5b4fc; }
        .search-box { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        input { flex: 1; padding: 0.75rem; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 1rem; }
        button { padding: 0.75rem 1.5rem; border-radius: 8px; border: none; background: #7c3aed; color: white; cursor: pointer; font-size: 1rem; }
        button:hover { background: #6d28d9; }
        select { padding: 0.75rem; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; }
        .controls { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .controls label { color: #888; font-size: 0.85rem; display: flex; align-items: center; gap: 0.25rem; }
        .controls input[type=checkbox] { accent-color: #7c3aed; }
        .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; transition: border-color 0.2s; }
        .result:hover { border-color: #7c3aed; }
        .result .meta { display: flex; gap: 1rem; margin-bottom: 0.5rem; }
        .result .score { color: #7c3aed; font-weight: bold; }
        .result .type { color: #22c55e; font-size: 0.85rem; }
        .result .text { color: #ccc; font-size: 0.9rem; }
        .result .actions { margin-top: 0.5rem; }
        .result .actions button { padding: 0.25rem 0.75rem; font-size: 0.8rem; background: #333; }
        .result .actions button:hover { background: #7c3aed; }
        .stats { color: #888; margin-bottom: 1rem; font-size: 0.9rem; }
        .group-header { color: #f59e0b; font-size: 1.1rem; margin: 1.5rem 0 0.5rem; border-bottom: 1px solid #333; padding-bottom: 0.25rem; }
        .record-card { }
        .record-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; }
        .record-id { color: #a5b4fc; font-family: monospace; font-size: 0.9rem; }
        .record-amount { color: #f59e0b; font-size: 1.2rem; font-weight: bold; }
        .record-fields { display: flex; gap: 1rem; margin-bottom: 0.5rem; }
        .field-val { color: #888; font-size: 0.85rem; }
        .items { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.4rem; }
        .item-chip { background: #262626; border: 1px solid #444; border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.8rem; color: #ccc; }
        .record-text { color: #ccc; font-size: 0.9rem; }
    </style></head><body>
    <h1>Procurement Search <span class="badge local">Local LLM</span> <span class="badge qdrant">Qdrant Cloud</span></h1>
    <p class="subtitle">nomic-embed-text (local) + Qdrant Prefetch/RRF Fusion, Discovery API, Recommend API, Grouping</p>
    <div class="search-box">
        <input id="q" placeholder="Search invoices, products, vendors..." autofocus />
        <select id="collection">
            <option value="DocumentChunk_text">Invoices</option>
            <option value="Entity_name">Entities</option>
            <option value="TextSummary_text">Summaries</option>
            <option value="TextDocument_name">Documents</option>
        </select>
        <button onclick="doSearch()">Search</button>
        <button onclick="askQuestion()" style="background:#22c55e">Ask (RAG)</button>
    </div>
    <div class="controls">
        <label><input type="checkbox" id="useFusion" checked /> Prefetch + RRF Fusion</label>
        <label><input type="checkbox" id="groupByType" /> Group by type</label>
        <label>Limit: <select id="limit"><option>10</option><option selected>20</option><option>50</option></select></label>
    </div>
    <div id="stats" class="stats"></div>
    <div id="results"></div>
    <script>
    let lastResults = [];

    async function doSearch() {
        const q = document.getElementById('q').value;
        if (!q) return;
        const c = document.getElementById('collection').value;
        const fusion = document.getElementById('useFusion').checked;
        const group = document.getElementById('groupByType').checked;
        const limit = document.getElementById('limit').value;
        document.getElementById('results').innerHTML = '<p style="color:#888">Embedding query locally & searching Qdrant...</p>';

        const url = group
            ? `/search/grouped?q=${encodeURIComponent(q)}&collection=${c}&limit=${limit}`
            : `/search?q=${encodeURIComponent(q)}&collection=${c}&limit=${limit}&use_fusion=${fusion}`;
        const res = await fetch(url);
        const data = await res.json();

        document.getElementById('stats').textContent =
            `${data.total || data.results?.length || 0} results in ${data.time_ms}ms | Embed: ${data.embed_ms}ms | Search: ${data.search_ms}ms`;

        if (group && data.groups) {
            document.getElementById('results').innerHTML = Object.entries(data.groups).map(([type, items]) => `
                <div class="group-header">${type} (${items.length})</div>
                ${items.map(renderResult).join('')}
            `).join('');
        } else {
            lastResults = data.results || [];
            document.getElementById('results').innerHTML = lastResults.map(renderResult).join('');
        }
    }

    function parseText(raw) {
        if (!raw) return null;
        try { return JSON.parse(raw.replace(/'/g, '"')); } catch(e) {
            try { return JSON.parse(raw); } catch(e2) { return null; }
        }
    }

    function formatRecord(raw) {
        const d = typeof raw === 'object' ? raw : parseText(raw);
        if (!d) return `<div class="record-text">${String(raw).slice(0,300)}</div>`;

        if (d.invoice_number || d.transaction_id) {
            const id = d.invoice_number || d.transaction_id;
            const amt = d.total || d.amount || 0;
            const date = d.date || '';
            const vendor = d.vendor_id ? `Vendor ${d.vendor_id}` : '';
            const discount = d.discount ? `<span class="field-val" style="color:#22c55e">Discount: $${Number(d.discount).toLocaleString()}</span>` : '';
            let itemsHtml = '';
            if (d.items) {
                let items = d.items;
                if (typeof items === 'string') { try { items = JSON.parse(items.replace(/'/g, '"')); } catch(e) { items = []; } }
                if (Array.isArray(items)) {
                    itemsHtml = '<div class="items">' + items.map(i =>
                        `<span class="item-chip">${i.product} x${i.qty} ($${Number(i.total).toLocaleString()})</span>`
                    ).join('') + '</div>';
                }
            }
            return `<div class="record-card">
                <div class="record-header">
                    <span class="record-id">${id}</span>
                    <span class="record-amount">$${Number(amt).toLocaleString()}</span>
                </div>
                <div class="record-fields">
                    <span class="field-val">${date}</span>
                    <span class="field-val">${vendor}</span>
                    ${discount}
                </div>
                ${itemsHtml}
            </div>`;
        }
        // Entity or other
        return `<div class="record-text">${String(d.text || d.name || JSON.stringify(d)).slice(0,200)}</div>`;
    }

    function renderResult(r) {
        return `<div class="result">
            <div class="meta">
                <span class="score">${r.score.toFixed(4)}</span>
                <span class="type">${r.type || ''}</span>
            </div>
            ${formatRecord(r.text)}
            <div class="actions">
                <button onclick="discover('${r.id}', true)">More like this</button>
                <button onclick="discover('${r.id}', false)">Less like this</button>
            </div>
        </div>`;
    }

    let positiveCtx = null, negativeCtx = null;

    async function discover(pointId, isPositive) {
        if (isPositive) { positiveCtx = pointId; } else { negativeCtx = pointId; }
        const q = document.getElementById('q').value || 'procurement';
        const c = document.getElementById('collection').value;
        let url = `/discover?q=${encodeURIComponent(q)}&collection=${c}`;
        if (positiveCtx) url += `&positive_id=${positiveCtx}`;
        if (negativeCtx) url += `&negative_id=${negativeCtx}`;
        const res = await fetch(url);
        const data = await res.json();
        const method = data.method === 'discovery_api' ? 'Discovery API (target + context pairs)'
            : data.method === 'recommend_api' ? 'Recommend API (positive/negative)'
            : 'Vector search';
        document.getElementById('stats').textContent = `${method}: ${data.results.length} results in ${data.time_ms}ms` +
            (positiveCtx ? ` | +${positiveCtx.slice(0,8)}` : '') + (negativeCtx ? ` | -${negativeCtx.slice(0,8)}` : '');
        document.getElementById('results').innerHTML = data.results.map(renderResult).join('');
    }

    async function askQuestion() {
        const q = document.getElementById('q').value;
        if (!q) return;
        const c = document.getElementById('collection').value;
        document.getElementById('results').innerHTML = '<p style="color:#888">Retrieving context via Qdrant Prefetch+Fusion, then asking LLM...</p>';
        const res = await fetch(`/ask?q=${encodeURIComponent(q)}&collection=${c}`);
        const data = await res.json();
        document.getElementById('stats').textContent = `RAG: ${data.sources} sources | Retrieval: ${data.retrieval_ms}ms | LLM: ${data.llm_ms}ms | Model: ${data.model}`;
        document.getElementById('results').innerHTML = `<div class="result" style="border-color:#22c55e"><div style="color:#22c55e;font-weight:bold;margin-bottom:0.5rem">Answer</div><div class="text" style="white-space:pre-wrap">${data.answer}</div></div>`;
    }

    document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });
    </script></body></html>
    """


@app.get("/search")
async def search(
    q: str = Query(...),
    collection: str = Query("DocumentChunk_text"),
    limit: int = Query(20, ge=1, le=100),
    use_fusion: bool = Query(True),
):
    """
    Qdrant Prefetch + RRF Fusion: fetch a broad candidate set, then fuse rankings.
    Two prefetch branches with different limits create a multi-stage pipeline.
    """
    t0 = time.time()
    query_vector = get_embedding(q)
    embed_ms = round((time.time() - t0) * 1000, 1)

    t1 = time.time()
    if use_fusion:
        # Multi-stage: two prefetches with different candidate pool sizes, fused with RRF
        results = qdrant.query_points(
            collection_name=collection,
            prefetch=[
                Prefetch(query=query_vector, using="text", limit=100),  # broad recall
                Prefetch(query=query_vector, using="text", limit=50),   # tighter precision
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
    else:
        results = qdrant.query_points(
            collection_name=collection,
            query=query_vector,
            using="text",
            limit=limit,
            with_payload=True,
        )
    search_ms = round((time.time() - t1) * 1000, 1)

    items = []
    for point in results.points:
        payload = point.payload or {}
        items.append({
            "id": str(point.id),
            "score": point.score,
            "text": payload.get("text", ""),
            "type": payload.get("type", ""),
            "payload": payload,
        })

    return {
        "query": q,
        "results": items,
        "total": len(items),
        "time_ms": round((time.time() - t0) * 1000, 1),
        "embed_ms": embed_ms,
        "search_ms": search_ms,
        "method": "prefetch_rrf_fusion" if use_fusion else "basic_query",
    }


@app.get("/search/grouped")
async def search_grouped(
    q: str = Query(...),
    collection: str = Query("DocumentChunk_text"),
    limit: int = Query(20),
):
    """Search with results grouped by payload 'type' field using Qdrant's group API."""
    t0 = time.time()
    query_vector = get_embedding(q)
    embed_ms = round((time.time() - t0) * 1000, 1)

    t1 = time.time()
    groups = qdrant.query_points_groups(
        collection_name=collection,
        query=query_vector,
        using="text",
        group_by="type",
        limit=limit,
        group_size=5,
        with_payload=True,
    )
    search_ms = round((time.time() - t1) * 1000, 1)

    result_groups = {}
    total = 0
    for group in groups.groups:
        key = str(group.id)
        result_groups[key] = []
        for hit in group.hits:
            payload = hit.payload or {}
            result_groups[key].append({
                "id": str(hit.id),
                "score": hit.score,
                "text": payload.get("text", ""),
                "type": payload.get("type", ""),
                "payload": payload,
            })
            total += 1

    return {
        "query": q,
        "groups": result_groups,
        "total": total,
        "time_ms": round((time.time() - t0) * 1000, 1),
        "embed_ms": embed_ms,
        "search_ms": search_ms,
    }


@app.get("/discover")
async def discover(
    q: str = Query(...),
    collection: str = Query("DocumentChunk_text"),
    positive_id: str = Query(None, description="Point ID to use as positive context"),
    negative_id: str = Query(None, description="Point ID to use as negative context"),
    limit: int = Query(20),
):
    """
    Qdrant Discovery API: search with a target vector constrained by context pairs.
    Uses DiscoverQuery with ContextPair(positive, negative) to steer results toward
    the positive example and away from the negative example.
    """
    t0 = time.time()
    query_vector = get_embedding(q)
    embed_ms = round((time.time() - t0) * 1000, 1)

    t1 = time.time()
    if positive_id and negative_id:
        # Full Discovery: target vector + context pair
        results = qdrant.query_points(
            collection_name=collection,
            query=DiscoverQuery(
                discover=DiscoverInput(
                    target=query_vector,
                    context=[ContextPair(positive=positive_id, negative=negative_id)],
                )
            ),
            using="text",
            limit=limit,
            with_payload=True,
        )
    elif positive_id:
        # Recommend with positive only
        results = qdrant.query_points(
            collection_name=collection,
            query=RecommendQuery(
                recommend=RecommendInput(
                    positive=[positive_id],
                    strategy=RecommendStrategy.AVERAGE_VECTOR,
                )
            ),
            using="text",
            limit=limit,
            with_payload=True,
        )
    elif negative_id:
        # Recommend with negative — find things unlike this point but matching query
        results = qdrant.query_points(
            collection_name=collection,
            query=RecommendQuery(
                recommend=RecommendInput(
                    positive=[query_vector],
                    negative=[negative_id],
                    strategy=RecommendStrategy.BEST_SCORE,
                )
            ),
            using="text",
            limit=limit,
            with_payload=True,
        )
    else:
        results = qdrant.query_points(
            collection_name=collection, query=query_vector, using="text", limit=limit, with_payload=True,
        )
    search_ms = round((time.time() - t1) * 1000, 1)

    items = []
    for point in results.points:
        payload = point.payload or {}
        items.append({
            "id": str(point.id),
            "score": point.score,
            "text": payload.get("text", ""),
            "type": payload.get("type", ""),
            "payload": payload,
        })

    return {
        "query": q,
        "positive_id": positive_id,
        "negative_id": negative_id,
        "results": items,
        "time_ms": round((time.time() - t0) * 1000, 1),
        "embed_ms": embed_ms,
        "search_ms": search_ms,
        "method": "discovery_api" if (positive_id and negative_id) else "recommend_api" if (positive_id or negative_id) else "basic_query",
    }


@app.get("/recommend")
async def recommend(
    positive_ids: str = Query(..., description="Comma-separated positive point IDs"),
    negative_ids: str = Query("", description="Comma-separated negative point IDs"),
    collection: str = Query("DocumentChunk_text"),
    strategy: str = Query("average_vector", description="average_vector or best_score"),
    limit: int = Query(10),
):
    """
    Qdrant Recommend API: find items similar to positive examples, dissimilar to negatives.
    Supports AVERAGE_VECTOR (default) and BEST_SCORE strategies.
    """
    t0 = time.time()
    pos = [pid.strip() for pid in positive_ids.split(",") if pid.strip()]
    neg = [pid.strip() for pid in negative_ids.split(",") if pid.strip()]
    strat = RecommendStrategy.BEST_SCORE if strategy == "best_score" else RecommendStrategy.AVERAGE_VECTOR

    results = qdrant.query_points(
        collection_name=collection,
        query=RecommendQuery(
            recommend=RecommendInput(
                positive=pos,
                negative=neg if neg else None,
                strategy=strat,
            )
        ),
        using="text",
        limit=limit,
        with_payload=True,
    )
    items = []
    for point in results.points:
        payload = point.payload or {}
        items.append({
            "id": str(point.id),
            "score": point.score,
            "text": payload.get("text", ""),
            "type": payload.get("type", ""),
        })
    return {
        "results": items,
        "time_ms": round((time.time() - t0) * 1000, 1),
        "method": f"recommend_{strategy}",
    }


@app.get("/filter")
async def filtered_search(
    q: str = Query(...),
    collection: str = Query("DocumentChunk_text"),
    type_filter: str = Query(None, description="Filter by type field"),
    limit: int = Query(20),
):
    """Semantic search with payload filter using indexed fields."""
    t0 = time.time()
    query_vector = get_embedding(q)

    query_filter = None
    if type_filter:
        query_filter = Filter(
            must=[FieldCondition(key="type", match=MatchValue(value=type_filter))]
        )

    results = qdrant.query_points(
        collection_name=collection,
        query=query_vector,
        using="text",
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
    )

    items = []
    for point in results.points:
        payload = point.payload or {}
        items.append({
            "id": str(point.id),
            "score": point.score,
            "text": payload.get("text", ""),
            "type": payload.get("type", ""),
        })
    return {"results": items, "time_ms": round((time.time() - t0) * 1000, 1)}


@app.get("/ask")
async def ask(q: str = Query(...), collection: str = Query("DocumentChunk_text"), limit: int = Query(5)):
    """
    RAG Q&A: retrieve relevant docs via Qdrant Prefetch+Fusion, then reason with LLM.
    Uses OpenRouter (free Qwen3-4B), Groq, or any OpenAI-compatible endpoint.
    """
    t0 = time.time()
    query_vector = get_embedding(q)

    # Retrieve context via Prefetch + RRF Fusion
    results = qdrant.query_points(
        collection_name=collection,
        prefetch=[
            Prefetch(query=query_vector, using="text", limit=50),
            Prefetch(query=query_vector, using="text", limit=20),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )

    context_docs = []
    for p in results.points:
        text = (p.payload or {}).get("text", "")
        context_docs.append(text[:500])

    context = "\n---\n".join(context_docs)
    retrieval_ms = round((time.time() - t0) * 1000, 1)

    # LLM reasoning via local Distil Labs model or cloud fallback
    t1 = time.time()
    try:
        answer = get_llm_response(
            "You are a procurement analyst. Answer questions using the provided context from invoices, transactions, and vendor data. Be specific with numbers and dates.",
            f"Context:\n{context}\n\nQuestion: {q}",
        )
    except Exception as e:
        answer = f"LLM error: {e}"
    llm_ms = round((time.time() - t1) * 1000, 1)

    model_name = get_model_name()
    return {
        "question": q,
        "answer": answer,
        "sources": len(context_docs),
        "retrieval_ms": retrieval_ms,
        "llm_ms": llm_ms,
        "model": model_name,
    }


@app.get("/collections")
async def list_collections():
    result = {}
    for c in COLLECTIONS:
        info = qdrant.get_collection(c)
        result[c] = {"points": info.points_count, "vectors_size": info.config.params.vectors.size}
    return result


# --- cognee integration: graph-aware search + knowledge ingestion ---


@app.get("/cognee-search")
async def cognee_search(q: str = Query(...), search_type: str = Query("INSIGHTS")):
    """
    cognee graph-aware search: queries the knowledge graph using vector similarity
    combined with graph traversal for deeper, relationship-aware results.

    Search types: CHUNKS, SUMMARIES, RAG_COMPLETION, GRAPH_COMPLETION, NATURAL_LANGUAGE
    """
    if not cognee_available:
        return {"error": "cognee not installed. Run: uv add cognee cognee-community-vector-adapter-qdrant"}

    t0 = time.time()
    try:
        st = getattr(SearchType, search_type.upper(), SearchType.CHUNKS)
        results = await cognee.search(query_text=q, query_type=st)
        items = [str(r) for r in results[:20]]
    except Exception as e:
        return {"error": f"cognee search failed: {e}", "time_ms": round((time.time() - t0) * 1000, 1)}

    return {
        "query": q,
        "search_type": search_type,
        "results": items,
        "total": len(items),
        "time_ms": round((time.time() - t0) * 1000, 1),
        "method": "cognee_graph_search",
    }


@app.post("/add-knowledge")
async def add_knowledge(text: str = Query(..., description="Text to ingest into the knowledge graph")):
    """
    Add new data to the cognee knowledge graph. Runs cognee.add() + cognee.cognify()
    to extract entities, relationships, and summaries, then stores in Qdrant.
    """
    if not cognee_available:
        return {"error": "cognee not installed. Run: uv add cognee cognee-community-vector-adapter-qdrant"}

    t0 = time.time()
    try:
        await cognee.add(text)
        await cognee.cognify()
    except Exception as e:
        return {"error": f"cognee ingestion failed: {e}", "time_ms": round((time.time() - t0) * 1000, 1)}

    return {
        "status": "ok",
        "message": "Knowledge ingested and graph updated.",
        "time_ms": round((time.time() - t0) * 1000, 1),
        "method": "cognee_ecl_pipeline",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
