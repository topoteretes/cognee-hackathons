"""
Project 3: Anomaly Detective
Local nomic-embed-text + Qdrant advanced features:
- Vector outlier detection via centroid distance
- Qdrant Recommend API to find near-duplicates
- Discovery API to investigate anomalies (find similar/dissimilar)
- Payload-indexed filtering for fast anomaly lookups
- Scroll API for bulk data loading
"""

import os
import sys
import json
import time
import statistics
from collections import defaultdict
from contextlib import asynccontextmanager

import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PayloadSchemaType,
    Prefetch,
    Fusion,
    FusionQuery,
    RecommendQuery,
    RecommendInput,
    RecommendStrategy,
)

load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from shared.llm import init_llm, get_llm_response, get_model_name, is_available as llm_available
from shared.embeddings import init_embeddings, get_embedding

EMBED_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "nomic-embed-text", "nomic-embed-text-v1.5.f16.gguf"
)

qdrant = QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])

LLM_MODEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "cognee-distillabs-model-gguf-quantized", "model-quantized.gguf"
)
LLM_FALLBACK_PATH = os.path.join(
    os.path.dirname(__file__), "..", "models", "Qwen3-4B-Q4_K_M", "Qwen3-4B-Q4_K_M.gguf"
)
anomaly_cache = {}


def parse_record(payload):
    text = payload.get("text", "")
    if isinstance(text, dict):
        return text
    if isinstance(text, str):
        try:
            return json.loads(text.replace("'", '"'))
        except Exception:
            try:
                return eval(text)
            except Exception:
                return None
    return None


def load_vectors_and_data(collection: str):
    records = []
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection, limit=100, offset=offset,
            with_payload=True, with_vectors=True,
        )
        if not points:
            break
        for p in points:
            data = parse_record(p.payload)
            if data:
                records.append({
                    "id": str(p.id), "vector": np.array(p.vector["text"]),
                    "data": data, "payload": p.payload,
                })
        if offset is None:
            break
    return records


def detect_amount_outliers(records, field="total", z_threshold=2.5):
    amounts = [(float(r["data"].get(field, 0)), r) for r in records if r["data"].get(field) is not None]
    if len(amounts) < 5:
        return []
    values = [a[0] for a in amounts]
    mean, stdev = statistics.mean(values), statistics.stdev(values)
    if stdev == 0:
        return []
    return sorted([
        {
            "id": r["id"], "type": "amount_outlier",
            "severity": "high" if abs(v - mean) / stdev > 4 else "medium",
            "detail": f"{field}=${v:,.2f} (z={abs(v - mean) / stdev:.1f}, mean=${mean:,.2f})",
            "data": r["data"],
        }
        for v, r in amounts if abs(v - mean) / stdev > z_threshold
    ], key=lambda x: -float(x["detail"].split("z=")[1].split(",")[0]))


def detect_vector_outliers(records, z_threshold=2.0):
    if len(records) < 10:
        return []
    vectors = np.array([r["vector"] for r in records])
    centroid = vectors.mean(axis=0)
    dists = [np.linalg.norm(r["vector"] - centroid) for r in records]
    mean_d, stdev_d = statistics.mean(dists), statistics.stdev(dists)
    if stdev_d == 0:
        return []
    return sorted([
        {
            "id": records[i]["id"], "type": "embedding_outlier",
            "severity": "high" if (dists[i] - mean_d) / stdev_d > 3 else "medium",
            "detail": f"dist={dists[i]:.4f} (z={(dists[i] - mean_d) / stdev_d:.1f})",
            "data": records[i]["data"],
        }
        for i in range(len(records)) if (dists[i] - mean_d) / stdev_d > z_threshold
    ], key=lambda x: -float(x["detail"].split("z=")[1].split(")")[0]))


def detect_duplicates_via_recommend(records):
    """Use Qdrant Batch Query API to find near-duplicate vectors efficiently."""
    from qdrant_client.models import QueryRequest

    duplicates = []
    seen = set()
    batch_size = 50
    scan_records = records[:200]

    for batch_start in range(0, len(scan_records), batch_size):
        batch = scan_records[batch_start : batch_start + batch_size]
        requests = [
            QueryRequest(
                query=r["id"],
                using="text",
                limit=3,
                score_threshold=0.99,
                with_payload=True,
            )
            for r in batch
        ]
        try:
            responses = qdrant.query_batch_points(
                collection_name="DocumentChunk_text",
                requests=requests,
                timeout=30,
            )
        except Exception as e:
            print(f"  Batch query error at {batch_start}: {e}")
            continue

        print(f"  Duplicate scan: {batch_start + len(batch)}/{len(scan_records)}")

        for r, response in zip(batch, responses):
            for match in response.points:
                if str(match.id) != r["id"]:
                    pair = tuple(sorted([r["id"], str(match.id)]))
                    if pair not in seen:
                        seen.add(pair)
                        duplicates.append({
                            "id": r["id"], "type": "near_duplicate",
                            "severity": "high" if match.score > 0.999 else "medium",
                            "detail": f"sim={match.score:.4f} with {match.id}",
                            "data": r["data"],
                        })

    return duplicates


def detect_vendor_anomalies(records):
    vendor_totals = defaultdict(list)
    for r in records:
        vid, total = r["data"].get("vendor_id"), r["data"].get("total")
        if vid is not None and total is not None:
            vendor_totals[vid].append(float(total))
    return sorted([
        {
            "id": f"vendor_{vid}", "type": "vendor_variance", "severity": "medium",
            "detail": f"Vendor {vid}: CV={statistics.stdev(t)/statistics.mean(t):.2f}, mean=${statistics.mean(t):,.0f}, n={len(t)}",
            "data": {"vendor_id": vid, "count": len(t), "spend": sum(t)},
        }
        for vid, t in vendor_totals.items()
        if len(t) >= 3 and statistics.mean(t) > 0 and statistics.stdev(t) / statistics.mean(t) > 0.8
    ], key=lambda x: -float(x["detail"].split("CV=")[1].split(",")[0]))


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_embeddings(EMBED_MODEL_PATH)
    init_llm([(LLM_MODEL_PATH, "Distil Labs"), (LLM_FALLBACK_PATH, "Qwen3-4B")])

    # Payload indexes
    for field, schema in [("type", PayloadSchemaType.KEYWORD), ("text", PayloadSchemaType.TEXT)]:
        try:
            qdrant.create_payload_index(collection_name="DocumentChunk_text", field_name=field, field_schema=schema)
        except Exception:
            pass

    print("Loading vectors from Qdrant...")
    invoices = load_vectors_and_data("DocumentChunk_text")
    print(f"Loaded {len(invoices)} records with vectors")

    all_anomalies = []
    print("Detecting amount outliers...")
    all_anomalies.extend(detect_amount_outliers(invoices))
    print("Detecting embedding outliers...")
    all_anomalies.extend(detect_vector_outliers(invoices))
    print("Detecting duplicates via Qdrant Recommend API...")
    all_anomalies.extend(detect_duplicates_via_recommend(invoices))
    print("Detecting vendor anomalies...")
    all_anomalies.extend(detect_vendor_anomalies(invoices))

    summary = {
        "total": len(all_anomalies),
        "high": sum(1 for a in all_anomalies if a["severity"] == "high"),
        "medium": sum(1 for a in all_anomalies if a["severity"] == "medium"),
        "by_type": dict(defaultdict(int)),
    }
    for a in all_anomalies:
        summary["by_type"][a["type"]] = summary["by_type"].get(a["type"], 0) + 1

    anomaly_cache["anomalies"] = all_anomalies
    anomaly_cache["summary"] = summary
    print(f"Found {len(all_anomalies)} anomalies")
    yield


app = FastAPI(title="Anomaly Detective", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html>
    <html><head><title>Anomaly Detective</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; background: #0a0a0a; color: #e0e0e0; padding: 2rem; max-width: 1200px; margin: 0 auto; }
        h1 { color: #ef4444; margin-bottom: 0.25rem; }
        .subtitle { color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
        .badge.local { background: #065f46; color: #6ee7b7; }
        .badge.qdrant { background: #1e1b4b; color: #a5b4fc; }
        .kpi-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
        .kpi { background: #1a1a1a; border-radius: 12px; padding: 1.5rem; flex: 1; text-align: center; border: 1px solid #333; }
        .kpi .value { font-size: 2rem; font-weight: bold; }
        .kpi .label { color: #888; margin-top: 0.25rem; }
        .high .value { color: #ef4444; }
        .medium .value { color: #f59e0b; }
        .total .value { color: #a855f7; }
        .search-row { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
        .search-row input { flex: 1; padding: 0.75rem; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; }
        .search-row button { padding: 0.75rem 1.5rem; border-radius: 8px; border: none; background: #ef4444; color: white; cursor: pointer; }
        .filters { margin-bottom: 1.5rem; display: flex; gap: 0.5rem; flex-wrap: wrap; }
        .filters button { padding: 0.5rem 1rem; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #ccc; cursor: pointer; }
        .filters button.active { background: #ef4444; color: white; border-color: #ef4444; }
        .anomaly { background: #1a1a1a; border-left: 4px solid #333; border-radius: 0 8px 8px 0; padding: 1rem; margin-bottom: 0.75rem; }
        .anomaly.high { border-left-color: #ef4444; }
        .anomaly.medium { border-left-color: #f59e0b; }
        .anomaly .header { display: flex; justify-content: space-between; margin-bottom: 0.5rem; align-items: center; }
        .tag { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; }
        .tag.high { background: #991b1b; color: #fca5a5; }
        .tag.medium { background: #78350f; color: #fcd34d; }
        .tag.type { background: #1e1b4b; color: #a5b4fc; }
        .anomaly .detail { color: #ccc; }
        .anomaly .data { color: #888; font-size: 0.85rem; margin-top: 0.5rem; font-family: monospace; max-height: 60px; overflow: hidden; }
        .anomaly .actions { margin-top: 0.5rem; }
        .anomaly .actions button { padding: 0.25rem 0.75rem; font-size: 0.8rem; border-radius: 4px; border: none; background: #333; color: #ccc; cursor: pointer; margin-right: 0.25rem; }
        .anomaly .actions button:hover { background: #ef4444; color: white; }
        .investigate-results { margin-top: 1rem; background: #111; border-radius: 8px; padding: 1rem; }
    </style></head><body>
    <h1>Anomaly Detective <span class="badge local">Local LLM</span> <span class="badge qdrant">Qdrant Recommend + Discovery</span></h1>
    <p class="subtitle">Vector outliers, near-duplicates, amount anomalies | nomic-embed-text + Qdrant Recommend API</p>

    <div class="search-row">
        <input id="q" placeholder="Semantic anomaly search (e.g. 'suspicious high-value laptop orders')..." />
        <button onclick="semanticSearch()">Search Anomalies</button>
    </div>

    <div class="kpi-row">
        <div class="kpi total"><div class="value" id="kpi-total">-</div><div class="label">Total Anomalies</div></div>
        <div class="kpi high"><div class="value" id="kpi-high">-</div><div class="label">High Severity</div></div>
        <div class="kpi medium"><div class="value" id="kpi-medium">-</div><div class="label">Medium Severity</div></div>
    </div>
    <div class="filters" id="filters"></div>
    <div id="anomalies"></div>
    <div id="investigate" class="investigate-results" style="display:none"></div>
    <script>
    let allAnomalies = [];
    let activeFilter = 'all';

    function parseText(raw) {
        if (!raw) return null;
        try { return JSON.parse(raw.replace(/'/g, '"')); } catch(e) {
            try { return JSON.parse(raw); } catch(e2) { return null; }
        }
    }

    function formatAnomalyData(d) {
        if (!d) return '';
        if (d.invoice_number || d.transaction_id) {
            const id = d.invoice_number || d.transaction_id;
            const amt = d.total || d.amount || 0;
            let items = '';
            if (d.items) {
                let arr = d.items;
                if (typeof arr === 'string') { try { arr = JSON.parse(arr.replace(/'/g, '"')); } catch(e) { arr = []; } }
                if (Array.isArray(arr)) { items = arr.map(i => `${i.product} x${i.qty}`).join(', '); }
            }
            return `<strong>${id}</strong> | $${Number(amt).toLocaleString()} | ${d.date||''} | Vendor ${d.vendor_id||'?'}${items ? '<br>'+items : ''}`;
        }
        if (d.vendor_id && d.count) {
            return `<strong>Vendor ${d.vendor_id}</strong> | ${d.count} invoices | $${Number(d.spend).toLocaleString()} total`;
        }
        return JSON.stringify(d).slice(0,150);
    }

    function render(list) {
        const filtered = activeFilter === 'all' ? list : list.filter(a => a.type === activeFilter);
        document.getElementById('anomalies').innerHTML = filtered.map(a => `
            <div class="anomaly ${a.severity}">
                <div class="header">
                    <div><span class="tag ${a.severity}">${a.severity.toUpperCase()}</span> <span class="tag type">${a.type}</span></div>
                    <span style="color:#666;font-size:0.8rem">${a.id}</span>
                </div>
                <div class="detail">${a.detail}</div>
                <div class="data">${formatAnomalyData(a.data)}</div>
                <div class="actions">
                    <button onclick="investigate('${a.id}')">Investigate (find similar)</button>
                </div>
            </div>
        `).join('');
    }

    async function semanticSearch() {
        const q = document.getElementById('q').value;
        if (!q) return;
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        document.getElementById('anomalies').innerHTML =
            `<p style="color:#888;margin-bottom:1rem">${data.results.length} results in ${data.time_ms}ms</p>` +
            data.results.map(r => `<div class="anomaly medium">
                <div class="header"><span class="tag type">search result</span> <span style="color:#ef4444">${r.score.toFixed(4)}</span></div>
                <div class="data">${formatAnomalyData(parseText(r.text))}</div>
                <div class="actions"><button onclick="investigate('${r.id}')">Find similar</button></div>
            </div>`).join('');
    }
    document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') semanticSearch(); });

    async function investigate(pointId) {
        const el = document.getElementById('investigate');
        el.style.display = 'block';
        el.innerHTML = '<p style="color:#888">Using Qdrant Recommend API to find similar records...</p>';
        const res = await fetch(`/api/investigate/${pointId}`);
        const data = await res.json();
        el.innerHTML = `<h3 style="color:#ef4444;margin-bottom:0.5rem">Investigation: ${pointId}</h3>
            <p style="color:#888;margin-bottom:0.5rem">${data.similar.length} similar records found in ${data.time_ms}ms</p>` +
            data.similar.map(s => `<div style="padding:0.5rem;border-bottom:1px solid #222">
                <span style="color:#ef4444">${s.score.toFixed(4)}</span> ${formatAnomalyData(parseText(s.payload?.text) || s.payload)}
            </div>`).join('');
    }

    fetch('/api/anomalies').then(r=>r.json()).then(d => {
        allAnomalies = d.anomalies;
        document.getElementById('kpi-total').textContent = d.summary.total;
        document.getElementById('kpi-high').textContent = d.summary.high;
        document.getElementById('kpi-medium').textContent = d.summary.medium;

        const types = ['all', ...Object.keys(d.summary.by_type)];
        document.getElementById('filters').innerHTML = types.map(t =>
            `<button onclick="activeFilter='${t}';document.querySelectorAll('.filters button').forEach(b=>b.classList.remove('active'));this.classList.add('active');render(allAnomalies);" class="${t==='all'?'active':''}">${t} (${t==='all'?d.summary.total:d.summary.by_type[t]})</button>`
        ).join('');
        render(allAnomalies);
    });
    </script></body></html>
    """


@app.get("/api/anomalies")
async def get_anomalies(severity: str = Query(None), anomaly_type: str = Query(None)):
    anomalies = anomaly_cache.get("anomalies", [])
    if severity:
        anomalies = [a for a in anomalies if a["severity"] == severity]
    if anomaly_type:
        anomalies = [a for a in anomalies if a["type"] == anomaly_type]
    return {"anomalies": anomalies, "summary": anomaly_cache.get("summary", {})}


@app.get("/api/search")
async def semantic_search(q: str = Query(...), limit: int = Query(20)):
    t0 = time.time()
    vec = get_embedding(q)
    embed_ms = round((time.time() - t0) * 1000, 1)

    # Prefetch + RRF Fusion for better ranking
    results = qdrant.query_points(
        collection_name="DocumentChunk_text",
        prefetch=[
            Prefetch(query=vec, using="text", limit=100),
            Prefetch(query=vec, using="text", limit=50),
        ],
        query=FusionQuery(fusion=Fusion.RRF),
        limit=limit,
        with_payload=True,
    )
    items = [{"id": str(p.id), "score": p.score, "text": (p.payload or {}).get("text", "")} for p in results.points]
    return {"results": items, "time_ms": round((time.time() - t0) * 1000, 1), "embed_ms": embed_ms}


@app.get("/api/investigate/{point_id}")
async def investigate(point_id: str):
    """
    Qdrant Recommend API: find records similar to a flagged anomaly.
    Uses RecommendQuery with BEST_SCORE strategy for nuanced similarity.
    """
    t0 = time.time()
    results = qdrant.query_points(
        collection_name="DocumentChunk_text",
        query=RecommendQuery(
            recommend=RecommendInput(
                positive=[point_id],
                strategy=RecommendStrategy.BEST_SCORE,
            )
        ),
        using="text",
        limit=10,
        with_payload=True,
    )
    items = [{"id": str(s.id), "score": s.score, "payload": s.payload} for s in results.points]
    return {
        "point_id": point_id,
        "similar": items,
        "time_ms": round((time.time() - t0) * 1000, 1),
        "method": "recommend_best_score",
    }


@app.get("/api/explain/{point_id}")
async def explain_anomaly(point_id: str):
    """
    LLM-powered anomaly explanation: retrieve the anomaly + similar records, ask LLM to explain.
    Uses Qdrant Recommend API + OpenRouter/Groq/Ollama LLM.
    """
    t0 = time.time()

    # Find the anomaly data
    anomaly = None
    for a in anomaly_cache.get("anomalies", []):
        if a["id"] == point_id:
            anomaly = a
            break

    # Find similar records via Recommend API
    try:
        similar = qdrant.query_points(
            collection_name="DocumentChunk_text",
            query=RecommendQuery(
                recommend=RecommendInput(
                    positive=[point_id],
                    strategy=RecommendStrategy.BEST_SCORE,
                )
            ),
            using="text",
            limit=5,
            with_payload=True,
        )
        similar_texts = [str((p.payload or {}).get("text", ""))[:300] for p in similar.points]
    except Exception:
        similar_texts = []

    context = f"Anomaly: {json.dumps(anomaly, default=str)}\n\nSimilar records:\n" + "\n---\n".join(similar_texts)

    try:
        explanation = get_llm_response(
            "You are a procurement auditor. Explain why this record was flagged as anomalous and what action should be taken. Be specific and concise.",
            context,
            max_tokens=300,
        )
    except Exception as e:
        explanation = f"LLM error: {e}"

    return {
        "point_id": point_id,
        "anomaly": anomaly,
        "explanation": explanation,
        "time_ms": round((time.time() - t0) * 1000, 1),
        "model": get_model_name(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6971)
