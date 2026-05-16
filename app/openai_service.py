from __future__ import annotations

import os
from typing import Iterable

from .models import QueryEvidence


class OpenAIService:
    """Thin OpenAI adapter for embeddings and grounded answer generation."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        self.last_error: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def status(self) -> dict[str, str | bool | None]:
        return {
            "enabled": self.enabled,
            "chat_model": self.chat_model,
            "embedding_model": self.embedding_model,
            "last_error": self.last_error,
        }

    def embed_texts(self, texts: list[str]) -> list[list[float]] | None:
        if not self.enabled or not texts:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.embeddings.create(model=self.embedding_model, input=texts)
            self.last_error = None
            return [item.embedding for item in response.data]
        except Exception as exc:  # pragma: no cover - requires a live OpenAI key/network
            self.last_error = str(exc)
            return None

    def embed_one(self, text: str) -> list[float] | None:
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else None

    def answer(self, question: str, evidence: Iterable[QueryEvidence], mode: str, fallback: str) -> tuple[str, dict[str, str | bool | None]]:
        evidence_list = list(evidence)
        if not self.enabled or not evidence_list:
            return fallback, {"llm_used": False, "reason": "OPENAI_API_KEY missing or no evidence"}
        context = "\n\n".join(
            f"Source: {item.title} ({item.source})\nRelevance: {item.score}\nSnippet: {item.snippet}"
            for item in evidence_list
        )
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)
            response = client.responses.create(
                model=self.chat_model,
                instructions=(
                    "You answer ecommerce customer questions for Askvio. "
                    "Use only the supplied retrieval context. If the answer is not in context, say what is missing. "
                    "Be concise, specific, and mention relevant constraints such as dates, prices, or conditions."
                ),
                input=(
                    f"Retrieval mode: {mode}\n"
                    f"Question: {question}\n\n"
                    f"Context:\n{context}\n\n"
                    "Answer the question using the context above."
                ),
                max_output_tokens=300,
            )
            self.last_error = None
            return response.output_text.strip(), {"llm_used": True, "model": self.chat_model}
        except Exception as exc:  # pragma: no cover - requires a live OpenAI key/network
            self.last_error = str(exc)
            return fallback, {"llm_used": False, "error": self.last_error}
