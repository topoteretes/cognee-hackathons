from fastapi.testclient import TestClient

from app import main
from app.main import app


HTML = b"""
<html><head><title>Shipping FAQ</title></head><body>
<h1>Shipping FAQ</h1>
<h2>Delivery</h2><p>Standard shipping takes five business days. Express shipping takes two business days.</p>
</body></html>
"""


def test_ingest_query_and_feedback_api():
    main._openai_service.api_key = None
    client = TestClient(app)

    ingest = client.post("/api/ingest", files=[("files", ("shipping.html", HTML, "text/html"))])
    assert ingest.status_code == 200
    assert ingest.json()["documents"] == 1

    query = client.post("/api/query", json={"question": "How long does express shipping take?", "session_id": "test"})
    assert query.status_code == 200
    body = query.json()
    assert "two business days" in body["wiki"]["answer"]
    assert body["vector"]["metrics"]["evidence_count"] >= 1
    assert body["vector"]["metrics"]["llm_used"] is False

    wiki = client.get("/api/wiki")
    assert wiki.status_code == 200
    assert wiki.json()["facts"]

    feedback = client.post(
        "/api/feedback",
        json={"question": "How long does express shipping take?", "correction": "VIP express shipping takes one business day.", "rating": 5, "session_id": "test"},
    )
    assert feedback.status_code == 200
    assert "VIP express shipping" in feedback.json()["promoted"]["promoted_fact"]
