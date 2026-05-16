from __future__ import annotations

import time
from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .html_processing import parse_html
from .memory import CogneePermanentMemory, RedisSessionMemory
from .models import HtmlDocument
from .retrieval import VectorKnowledgeBase, WikiKnowledgeBase, result_to_dict

app = FastAPI(title="Askvio Wiki Memory PoC", version="0.1.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

_documents: list[HtmlDocument] = []
_vector_kb = VectorKnowledgeBase()
_wiki_kb = WikiKnowledgeBase()
_session_memory = RedisSessionMemory()
_cognee_memory = CogneePermanentMemory()
_last_build: dict = {"documents": 0, "vector": {}, "wiki": {}, "cognee": {}}


class QueryRequest(BaseModel):
    question: str = Field(min_length=2)
    session_id: str = "demo"


class FeedbackRequest(BaseModel):
    question: str = Field(min_length=2)
    correction: str = Field(min_length=2)
    rating: int = Field(ge=1, le=5)
    session_id: str = "demo"


@app.get("/")
def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/api/status")
def status() -> dict:
    return {
        "documents": len(_documents),
        "last_build": _last_build,
        "redis": {"url": _session_memory.url, "available": _session_memory.available},
    }


@app.post("/api/ingest")
async def ingest(files: Annotated[list[UploadFile], File(description="One or more ecommerce HTML files")]) -> dict:
    global _documents, _last_build
    started = time.perf_counter()
    parsed: list[HtmlDocument] = []
    for file in files:
        content = await file.read()
        parsed.append(parse_html(file.filename, content.decode("utf-8", errors="ignore")))
        _session_memory.event("ingest", "raw_html_uploaded", {"filename": file.filename, "bytes": len(content)})

    _documents = parsed
    _vector_kb.build(_documents)
    _wiki_kb.build(_documents)
    lint_metrics = _wiki_kb.lint()
    cognee_metrics = await _cognee_memory.remember_documents(_documents)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    _last_build = {
        "documents": len(_documents),
        "vector": _vector_kb.stats(),
        "wiki": {**_wiki_kb.stats(), **lint_metrics},
        "cognee": cognee_metrics,
        "elapsed_ms": elapsed_ms,
    }
    _session_memory.event("ingest", "kb_built", _last_build)
    return _last_build


@app.post("/api/query")
def query(payload: QueryRequest) -> dict:
    started = time.perf_counter()
    vector = _vector_kb.query(payload.question)
    vector_ms = round((time.perf_counter() - started) * 1000, 2)

    started = time.perf_counter()
    wiki = _wiki_kb.query(payload.question)
    wiki_ms = round((time.perf_counter() - started) * 1000, 2)

    vector_dict = result_to_dict(vector)
    wiki_dict = result_to_dict(wiki)
    vector_dict["metrics"]["latency_ms"] = vector_ms
    wiki_dict["metrics"]["latency_ms"] = wiki_ms
    comparison = {
        "wiki_evidence_delta": wiki_dict["metrics"].get("evidence_count", 0) - vector_dict["metrics"].get("evidence_count", 0),
        "wiki_top_score_delta": round(wiki_dict["metrics"].get("top_score", 0) - vector_dict["metrics"].get("top_score", 0), 4),
        "fastest": "wiki" if wiki_ms <= vector_ms else "vector",
    }
    _session_memory.event(
        payload.session_id,
        "query_compared",
        {"question": payload.question, "vector": vector_dict["metrics"], "wiki": wiki_dict["metrics"], "comparison": comparison},
    )
    return {"question": payload.question, "vector": vector_dict, "wiki": wiki_dict, "comparison": comparison}


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest) -> dict:
    _session_memory.event(payload.session_id, "human_feedback", payload.model_dump())
    promoted = _wiki_kb.apply_feedback(payload.question, payload.correction, payload.rating)
    lint_metrics = _wiki_kb.lint()
    _session_memory.event(payload.session_id, "feedback_distilled_to_wiki", {**promoted, **lint_metrics})
    return {"wiki": _wiki_kb.stats(), "promoted": promoted, "lint": lint_metrics, "session_events": _session_memory.recent(payload.session_id, 5)}
