from app.html_processing import parse_html
from app.retrieval import VectorKnowledgeBase, WikiKnowledgeBase

HTML = """
<html><head><title>Violet Sneakers</title></head><body>
<h1>Violet Sneakers</h1>
<h2>Returns</h2><p>Violet Sneakers can be returned within 30 days if unworn.</p>
<h2>Shipping</h2><p>Express shipping arrives in two business days.</p>
</body></html>
"""


def test_vector_and_wiki_answer_uploaded_html():
    document = parse_html("product.html", HTML)
    vector = VectorKnowledgeBase()
    wiki = WikiKnowledgeBase()
    vector.build([document])
    wiki.build([document])

    vector_answer = vector.query("How long can I return Violet Sneakers?")
    wiki_answer = wiki.query("How long can I return Violet Sneakers?")

    assert "30 days" in vector_answer.answer
    assert "30 days" in wiki_answer.answer
    assert vector_answer.metrics["chunks_searched"] > 0
    assert wiki_answer.metrics["facts_searched"] > 0


def test_feedback_is_promoted_to_wiki_fact():
    wiki = WikiKnowledgeBase()
    wiki.build([])

    result = wiki.apply_feedback("What warranty is included?", "The warranty lasts two years.", 5)
    answer = wiki.query("What warranty is included?")

    assert result["rating"] == 5
    assert "two years" in answer.answer


def test_vector_kb_uses_openai_embedding_backend_when_vectors_are_supplied():
    document = parse_html("product.html", HTML)
    vector = VectorKnowledgeBase()
    vector.build([document])
    vector.set_embedding_vectors([[1.0, 0.0] for _ in vector.chunks])

    result = vector.query("Tell me about returns", query_embedding=[1.0, 0.0])

    assert result.metrics["search_backend"] == "openai_embeddings"
    assert result.metrics["top_score"] == 1.0
