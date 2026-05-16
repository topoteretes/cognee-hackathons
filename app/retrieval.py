from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Iterable

from .html_processing import clean_text, split_sentences
from .models import AnswerResult, HtmlDocument, QueryEvidence

TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}")
STOPWORDS = {
    "about", "after", "again", "also", "and", "are", "ask", "can", "does", "for", "from",
    "have", "how", "into", "its", "our", "the", "this", "that", "their", "there", "they", "what",
    "when", "where", "which", "will", "with", "your", "you", "why", "who", "was", "were", "is", "to",
    "a", "an", "of", "in", "on", "or", "by", "it", "as", "be", "we", "i",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]


def term_vector(text: str) -> Counter[str]:
    return Counter(tokenize(text))


def cosine(left: Counter[str], right: Counter[str]) -> float:
    if not left or not right:
        return 0.0
    overlap = set(left) & set(right)
    numerator = sum(left[t] * right[t] for t in overlap)
    left_norm = math.sqrt(sum(v * v for v in left.values()))
    right_norm = math.sqrt(sum(v * v for v in right.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


def chunk_text(text: str, max_words: int = 90) -> list[str]:
    sentences = split_sentences(text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in sentences:
        words = sentence.split()
        if current and current_words + len(words) > max_words:
            chunks.append(clean_text(" ".join(current)))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += len(words)
    if current:
        chunks.append(clean_text(" ".join(current)))
    return chunks or ([clean_text(text)] if clean_text(text) else [])


def synthesize_answer(question: str, snippets: Iterable[str], fallback: str) -> str:
    query_vec = term_vector(question)
    candidates: list[tuple[float, str]] = []
    for snippet in snippets:
        for sentence in split_sentences(snippet):
            candidates.append((cosine(query_vec, term_vector(sentence)), sentence))
    candidates.sort(key=lambda item: item[0], reverse=True)
    useful = [sentence for score, sentence in candidates[:3] if score > 0]
    if not useful:
        return fallback
    return " ".join(useful)


class VectorKnowledgeBase:
    """Classical vector-style retrieval baseline using deterministic local term vectors."""

    def __init__(self) -> None:
        self.chunks: list[dict[str, str]] = []
        self._vectors: list[Counter[str]] = []

    def build(self, documents: list[HtmlDocument]) -> None:
        self.chunks = []
        self._vectors = []
        for doc in documents:
            for index, chunk in enumerate(chunk_text(doc.text)):
                record = {
                    "id": f"{doc.doc_id}:chunk:{index}",
                    "doc_id": doc.doc_id,
                    "title": doc.title,
                    "source": doc.filename,
                    "text": chunk,
                }
                self.chunks.append(record)
                self._vectors.append(term_vector(chunk))

    def query(self, question: str, k: int = 4) -> AnswerResult:
        query_vec = term_vector(question)
        ranked = sorted(
            ((cosine(query_vec, vector), chunk) for vector, chunk in zip(self._vectors, self.chunks)),
            key=lambda item: item[0],
            reverse=True,
        )[:k]
        evidence = [
            QueryEvidence(source=chunk["source"], title=chunk["title"], snippet=chunk["text"], score=round(score, 4))
            for score, chunk in ranked
            if score > 0
        ]
        answer = synthesize_answer(
            question,
            [item.snippet for item in evidence],
            "The vector baseline did not find a matching passage in the uploaded HTML.",
        )
        return AnswerResult(
            answer=answer,
            evidence=evidence,
            metrics={
                "retrieval_mode": "vector",
                "chunks_searched": len(self.chunks),
                "evidence_count": len(evidence),
                "top_score": evidence[0].score if evidence else 0,
            },
        )

    def stats(self) -> dict[str, int]:
        return {"chunks": len(self.chunks)}


class WikiKnowledgeBase:
    """Wiki-style KB that promotes HTML into canonical pages, sections, and fact cards."""

    def __init__(self) -> None:
        self.pages: dict[str, dict] = {}
        self.facts: list[dict[str, str]] = []
        self.entity_index: dict[str, set[str]] = defaultdict(set)

    def build(self, documents: list[HtmlDocument]) -> None:
        self.pages = {}
        self.facts = []
        self.entity_index = defaultdict(set)
        for doc in documents:
            page = {
                "id": doc.doc_id,
                "title": doc.title,
                "source": doc.filename,
                "url": doc.url,
                "summary": self._summarize(doc),
                "sections": doc.sections,
            }
            self.pages[doc.doc_id] = page
            for section in doc.sections:
                for sentence in split_sentences(section["text"]):
                    if len(sentence.split()) < 4:
                        continue
                    fact = {
                        "page_id": doc.doc_id,
                        "title": doc.title,
                        "source": doc.filename,
                        "heading": section["heading"],
                        "text": sentence,
                    }
                    self.facts.append(fact)
                    for entity in self._entities(sentence + " " + section["heading"]):
                        self.entity_index[entity].add(doc.doc_id)

    def lint(self) -> dict[str, int]:
        seen: set[str] = set()
        deduped: list[dict[str, str]] = []
        removed = 0
        for fact in self.facts:
            key = clean_text(fact["text"].lower())
            if key in seen:
                removed += 1
                continue
            seen.add(key)
            deduped.append(fact)
        self.facts = deduped
        return {"duplicate_facts_removed": removed, "facts_after_lint": len(self.facts)}

    def query(self, question: str, k: int = 6) -> AnswerResult:
        query_vec = term_vector(question)
        query_entities = set(self._entities(question))
        ranked: list[tuple[float, dict[str, str]]] = []
        for fact in self.facts:
            text = f"{fact['title']} {fact['heading']} {fact['text']}"
            score = cosine(query_vec, term_vector(text))
            if query_entities & set(self._entities(text)):
                score += 0.15
            ranked.append((score, fact))
        ranked.sort(key=lambda item: item[0], reverse=True)
        best = [(score, fact) for score, fact in ranked[:k] if score > 0]
        evidence = [
            QueryEvidence(
                source=fact["source"],
                title=f"{fact['title']} / {fact['heading']}",
                snippet=fact["text"],
                score=round(score, 4),
            )
            for score, fact in best
        ]
        answer = synthesize_answer(
            question,
            [item.snippet for item in evidence],
            "The wiki has no fact card that matches this question yet. Add feedback to teach it.",
        )
        return AnswerResult(
            answer=answer,
            evidence=evidence,
            metrics={
                "retrieval_mode": "wiki",
                "pages": len(self.pages),
                "facts_searched": len(self.facts),
                "linked_entities": sum(len(v) for v in self.entity_index.values()),
                "evidence_count": len(evidence),
                "top_score": evidence[0].score if evidence else 0,
            },
        )

    def apply_feedback(self, question: str, correction: str, rating: int) -> dict[str, str | int]:
        page_id = "feedback"
        self.pages.setdefault(
            page_id,
            {"id": page_id, "title": "Human Feedback", "source": "feedback", "url": None, "summary": "Corrections supplied by users.", "sections": []},
        )
        fact = {
            "page_id": page_id,
            "title": "Human Feedback",
            "source": "feedback",
            "heading": f"Rating {rating} correction",
            "text": f"When asked '{question}', prefer this corrected answer: {correction}",
        }
        self.facts.append(fact)
        for entity in self._entities(question + " " + correction):
            self.entity_index[entity].add(page_id)
        return {"promoted_fact": fact["text"], "rating": rating}

    def stats(self) -> dict[str, int]:
        return {"pages": len(self.pages), "facts": len(self.facts), "entities": len(self.entity_index)}

    @staticmethod
    def _summarize(doc: HtmlDocument) -> str:
        sentences = split_sentences(doc.text)
        return " ".join(sentences[:2]) if sentences else doc.title

    @staticmethod
    def _entities(text: str) -> list[str]:
        candidates = re.findall(r"\b[A-Z][A-Za-z0-9&-]*(?:\s+[A-Z][A-Za-z0-9&-]*){0,3}", text)
        return [clean_text(candidate) for candidate in candidates if len(candidate) > 2]


def result_to_dict(result: AnswerResult) -> dict:
    return {
        "answer": result.answer,
        "evidence": [asdict(item) for item in result.evidence],
        "metrics": result.metrics,
    }
