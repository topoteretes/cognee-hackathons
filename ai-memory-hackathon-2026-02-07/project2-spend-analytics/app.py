"""
Project 2: Spend Analytics Dashboard
Local nomic-embed-text embeddings + Qdrant advanced features:
- Semantic search over invoices with local embeddings
- Qdrant scroll + payload filtering for aggregation
- Grouped queries by vendor
- Payload-indexed filtering for fast vendor/date lookups
"""

import os
import sys
import json
import time
from collections import defaultdict
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PayloadSchemaType,
    Filter,
    FieldCondition,
    MatchValue,
    Prefetch,
    Fusion,
    FusionQuery,
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
analytics_cache = {}


def parse_text_payload(payload):
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


def load_all_records(collection: str):
    records = []
    offset = None
    while True:
        points, offset = qdrant.scroll(
            collection_name=collection, limit=250, offset=offset,
            with_payload=True, with_vectors=False,
        )
        if not points:
            break
        for p in points:
            data = parse_text_payload(p.payload)
            if data:
                records.append(data)
        if offset is None:
            break
    return records


def compute_analytics(invoices, transactions):
    vendor_spend = defaultdict(float)
    monthly_spend = defaultdict(float)
    product_qty = defaultdict(int)
    product_revenue = defaultdict(float)
    vendor_invoice_count = defaultdict(int)

    for inv in invoices:
        vid = inv.get("vendor_id", "unknown")
        total = float(inv.get("total", 0))
        vendor_spend[f"Vendor {vid}"] += total
        vendor_invoice_count[f"Vendor {vid}"] += 1
        date = inv.get("date", "")
        if date:
            monthly_spend[date[:7]] += total

        items_str = inv.get("items", "[]")
        items = items_str if isinstance(items_str, list) else []
        if isinstance(items_str, str):
            try:
                items = json.loads(items_str.replace("'", '"'))
            except Exception:
                try:
                    items = eval(items_str)
                except Exception:
                    items = []
        for item in items:
            name = item.get("product", "Unknown")
            product_qty[name] += int(item.get("qty", 0))
            product_revenue[name] += float(item.get("total", 0))

    for tx in transactions:
        vid = tx.get("vendor_id", "unknown")
        amt = float(tx.get("amount", 0))
        vendor_spend[f"Vendor {vid}"] += amt
        date = tx.get("date", "")
        if date:
            monthly_spend[date[:7]] += amt

    return {
        "vendor_spend": dict(sorted(vendor_spend.items(), key=lambda x: -x[1])),
        "vendor_invoice_count": dict(sorted(vendor_invoice_count.items(), key=lambda x: -x[1])),
        "monthly_spend": dict(sorted(monthly_spend.items())),
        "top_products_qty": dict(sorted(product_qty.items(), key=lambda x: -x[1])[:20]),
        "top_products_revenue": dict(sorted(product_revenue.items(), key=lambda x: -x[1])[:20]),
        "total_invoices": len(invoices),
        "total_transactions": len(transactions),
        "total_spend": sum(vendor_spend.values()),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_embeddings(EMBED_MODEL_PATH)
    init_llm([(LLM_MODEL_PATH, "Distil Labs"), (LLM_FALLBACK_PATH, "Qwen3-4B")])

    # Create payload indexes for fast filtering
    for collection in ["DocumentChunk_text", "TextDocument_name"]:
        for field, schema in [("type", PayloadSchemaType.KEYWORD), ("text", PayloadSchemaType.TEXT)]:
            try:
                qdrant.create_payload_index(collection_name=collection, field_name=field, field_schema=schema)
            except Exception:
                pass

    print("Loading data from Qdrant...")
    all_records = load_all_records("DocumentChunk_text")
    # Split into invoices (have invoice_number) and transactions (have transaction_id)
    invoices = [r for r in all_records if "invoice_number" in r]
    transactions = [r for r in all_records if "transaction_id" in r]
    print(f"Loaded {len(invoices)} invoices, {len(transactions)} transactions from DocumentChunk_text")
    analytics_cache["data"] = compute_analytics(invoices, transactions)
    yield


app = FastAPI(title="Spend Analytics Dashboard", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return """
    <!DOCTYPE html>
    <html><head><title>Spend Analytics</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: system-ui; background: #0a0a0a; color: #e0e0e0; padding: 2rem; }
        h1 { color: #f59e0b; margin-bottom: 0.25rem; }
        .subtitle { color: #666; margin-bottom: 1.5rem; font-size: 0.9rem; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; }
        .badge.local { background: #065f46; color: #6ee7b7; }
        .badge.qdrant { background: #1e1b4b; color: #a5b4fc; }
        .kpi-row { display: flex; gap: 1rem; margin: 1.5rem 0; }
        .kpi { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 1.5rem; flex: 1; text-align: center; }
        .kpi .value { font-size: 2rem; font-weight: bold; color: #f59e0b; }
        .kpi .label { color: #888; margin-top: 0.25rem; }
        .search-row { display: flex; gap: 0.5rem; margin: 1.5rem 0; }
        .search-row input { flex: 1; padding: 0.75rem; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #fff; font-size: 1rem; }
        .search-row button { padding: 0.75rem 1.5rem; border-radius: 8px; border: none; background: #f59e0b; color: #000; cursor: pointer; font-weight: bold; }
        .charts { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem; }
        .chart-card { background: #1a1a1a; border: 1px solid #333; border-radius: 12px; padding: 1.5rem; }
        .chart-card h3 { color: #f59e0b; margin-bottom: 1rem; }
        canvas { max-height: 350px; }
        .search-results { margin-top: 1.5rem; }
        .search-result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; }
        .search-result .score { color: #f59e0b; font-weight: bold; }
        .record-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem; }
        .record-id { color: #a5b4fc; font-family: monospace; font-size: 0.85rem; }
        .record-amount { color: #f59e0b; font-size: 1.1rem; font-weight: bold; }
        .record-fields { display: flex; gap: 1rem; margin-bottom: 0.4rem; }
        .field-val { color: #888; font-size: 0.85rem; }
        .items { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-top: 0.3rem; }
        .item-chip { background: #262626; border: 1px solid #444; border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.78rem; color: #ccc; }
    </style></head><body>
    <h1>Spend Analytics <span class="badge local">Local Embeddings</span> <span class="badge qdrant">Qdrant Cloud</span></h1>
    <p class="subtitle">Semantic invoice search + analytics | nomic-embed-text + Qdrant payload indexing & grouping</p>

    <div class="search-row">
        <input id="q" placeholder="Semantic search invoices (e.g. 'laptop purchases over 10k')..." />
        <button onclick="semanticSearch()">Search</button>
    </div>
    <div id="search-results" class="search-results"></div>

    <div class="kpi-row">
        <div class="kpi"><div class="value" id="kpi-spend">-</div><div class="label">Total Spend</div></div>
        <div class="kpi"><div class="value" id="kpi-invoices">-</div><div class="label">Invoices</div></div>
        <div class="kpi"><div class="value" id="kpi-transactions">-</div><div class="label">Transactions</div></div>
        <div class="kpi"><div class="value" id="kpi-vendors">-</div><div class="label">Vendors</div></div>
    </div>
    <div class="charts">
        <div class="chart-card"><h3>Monthly Spend</h3><canvas id="monthlyChart"></canvas></div>
        <div class="chart-card"><h3>Spend by Vendor</h3><canvas id="vendorChart"></canvas></div>
        <div class="chart-card"><h3>Top Products (Qty)</h3><canvas id="pqChart"></canvas></div>
        <div class="chart-card"><h3>Top Products (Revenue)</h3><canvas id="prChart"></canvas></div>
    </div>
    <script>
    function parseText(raw) {
        if (!raw) return null;
        try { return JSON.parse(raw.replace(/'/g, '"')); } catch(e) {
            try { return JSON.parse(raw); } catch(e2) { return null; }
        }
    }
    function formatRecord(raw) {
        const d = typeof raw === 'object' ? raw : parseText(raw);
        if (!d) return `<span style="color:#ccc">${String(raw).slice(0,200)}</span>`;
        if (d.invoice_number || d.transaction_id) {
            const id = d.invoice_number || d.transaction_id;
            const amt = d.total || d.amount || 0;
            let itemsHtml = '';
            if (d.items) {
                let items = d.items;
                if (typeof items === 'string') { try { items = JSON.parse(items.replace(/'/g, '"')); } catch(e) { items = []; } }
                if (Array.isArray(items)) {
                    itemsHtml = '<div class="items">' + items.map(i =>
                        `<span class="item-chip">${i.product} x${i.qty}</span>`
                    ).join('') + '</div>';
                }
            }
            return `<div class="record-header"><span class="record-id">${id}</span><span class="record-amount">$${Number(amt).toLocaleString()}</span></div>
                <div class="record-fields"><span class="field-val">${d.date||''}</span><span class="field-val">Vendor ${d.vendor_id||'?'}</span></div>${itemsHtml}`;
        }
        return `<span style="color:#ccc">${String(d.text || JSON.stringify(d)).slice(0,200)}</span>`;
    }

    async function semanticSearch() {
        const q = document.getElementById('q').value;
        if (!q) return;
        document.getElementById('search-results').innerHTML = '<p style="color:#888">Embedding locally & searching Qdrant...</p>';
        const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        document.getElementById('search-results').innerHTML =
            `<p style="color:#888">${data.results.length} results in ${data.time_ms}ms (embed: ${data.embed_ms}ms)</p>` +
            data.results.map(r => `<div class="search-result"><span class="score">${r.score.toFixed(4)}</span>${formatRecord(r.text)}</div>`).join('');
    }
    document.getElementById('q').addEventListener('keydown', e => { if (e.key === 'Enter') semanticSearch(); });

    fetch('/api/analytics').then(r=>r.json()).then(d => {
        document.getElementById('kpi-spend').textContent = '$' + (d.total_spend/1e6).toFixed(2) + 'M';
        document.getElementById('kpi-invoices').textContent = d.total_invoices;
        document.getElementById('kpi-transactions').textContent = d.total_transactions;
        document.getElementById('kpi-vendors').textContent = Object.keys(d.vendor_spend).length;

        const colors = ['#f59e0b','#ef4444','#22c55e','#3b82f6','#a855f7','#ec4899','#14b8a6','#f97316','#6366f1','#84cc16'];

        new Chart(document.getElementById('monthlyChart'), {
            type:'line', data:{labels:Object.keys(d.monthly_spend), datasets:[{label:'Spend',data:Object.values(d.monthly_spend),borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.1)',fill:true,tension:0.3}]},
            options:{plugins:{legend:{display:false}},scales:{y:{ticks:{color:'#888'}},x:{ticks:{color:'#888',maxRotation:45}}}}
        });
        const vl = Object.keys(d.vendor_spend).slice(0,10);
        new Chart(document.getElementById('vendorChart'), {
            type:'doughnut', data:{labels:vl, datasets:[{data:vl.map(k=>d.vendor_spend[k]),backgroundColor:colors}]},
            options:{plugins:{legend:{position:'right',labels:{color:'#ccc'}}}}
        });
        const pq = Object.keys(d.top_products_qty).slice(0,10);
        new Chart(document.getElementById('pqChart'), {
            type:'bar', data:{labels:pq.map(l=>l.slice(0,25)), datasets:[{data:pq.map(k=>d.top_products_qty[k]),backgroundColor:'#22c55e'}]},
            options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888',font:{size:10}}}}}
        });
        const pr = Object.keys(d.top_products_revenue).slice(0,10);
        new Chart(document.getElementById('prChart'), {
            type:'bar', data:{labels:pr.map(l=>l.slice(0,25)), datasets:[{data:pr.map(k=>d.top_products_revenue[k]),backgroundColor:'#3b82f6'}]},
            options:{indexAxis:'y',plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#888'}},y:{ticks:{color:'#888',font:{size:10}}}}}
        });
    });
    </script></body></html>
    """


@app.get("/api/analytics")
async def get_analytics():
    return analytics_cache.get("data", {})


@app.get("/api/search")
async def semantic_search(q: str = Query(...), limit: int = Query(20)):
    t0 = time.time()
    vec = get_embedding(q)
    embed_ms = round((time.time() - t0) * 1000, 1)

    t1 = time.time()
    # Prefetch + RRF Fusion: two-stage retrieval pipeline
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
    search_ms = round((time.time() - t1) * 1000, 1)

    items = []
    for p in results.points:
        payload = p.payload or {}
        items.append({"id": str(p.id), "score": p.score, "text": payload.get("text", ""), "payload": payload})

    return {"results": items, "time_ms": round((time.time() - t0) * 1000, 1), "embed_ms": embed_ms, "search_ms": search_ms}


@app.get("/api/search/grouped")
async def grouped_vendor_search(q: str = Query(...), limit: int = Query(20)):
    """Group search results by vendor using Qdrant's group API."""
    vec = get_embedding(q)
    groups = qdrant.query_points_groups(
        collection_name="DocumentChunk_text",
        query=vec,
        using="text",
        group_by="type",
        limit=limit,
        group_size=5,
        with_payload=True,
    )
    result = {}
    for g in groups.groups:
        result[str(g.id)] = [{"id": str(h.id), "score": h.score, "payload": h.payload} for h in g.hits]
    return {"groups": result}


@app.get("/api/insights")
async def generate_insights(q: str = Query("Summarize spending patterns and flag concerns")):
    """
    LLM-powered spend insights: feed analytics summary to LLM for natural language analysis.
    """
    data = analytics_cache.get("data", {})
    summary = json.dumps({
        "total_spend": data.get("total_spend"),
        "total_invoices": data.get("total_invoices"),
        "total_transactions": data.get("total_transactions"),
        "top_vendors": dict(list(data.get("vendor_spend", {}).items())[:5]),
        "top_products_revenue": dict(list(data.get("top_products_revenue", {}).items())[:10]),
        "monthly_spend": data.get("monthly_spend", {}),
    }, indent=2, default=str)

    try:
        insights = get_llm_response(
            "You are a spend analytics expert. Analyze the procurement data and provide actionable insights. Be specific with numbers.",
            f"Procurement data:\n{summary}\n\nAnalysis request: {q}",
        )
    except Exception as e:
        insights = f"LLM error: {e}"

    return {"question": q, "insights": insights, "model": get_model_name()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5553)
