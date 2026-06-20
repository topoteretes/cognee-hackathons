"""
Unified embedding interface: local GGUF (dev) or remote API (prod).

Set EMBED_MODE=local (default) for llama-cpp-python with nomic-embed-text GGUF.
Set EMBED_MODE=remote for an OpenAI-compatible embeddings API.

Environment variables:
    EMBED_MODE       - "local" or "remote" (default: local)
    EMBED_API_URL    - API base URL for remote mode
    EMBED_API_KEY    - API key for remote mode
    EMBED_MODEL_NAME - Model name for remote mode (default: nomic-embed-text)
"""

import os
import requests

_local_model = None
_mode = None


def _get_mode():
    return os.getenv("EMBED_MODE", "local")


def init_embeddings(model_path: str | None = None):
    """Initialize the embedding backend."""
    global _local_model, _mode
    _mode = _get_mode()

    if _mode == "remote":
        print(f"Embedding mode: remote ({os.getenv('EMBED_API_URL', 'not set')})")
        return

    from llama_cpp import Llama
    if model_path and os.path.exists(model_path):
        print("Loading nomic-embed-text model...")
        _local_model = Llama(
            model_path=model_path,
            embedding=True,
            n_ctx=2048,
            n_batch=512,
            verbose=False,
        )
        print("Embedding model loaded.")
    else:
        print(f"WARNING: Embedding model not found at {model_path}")


def get_embedding(text: str) -> list[float]:
    """Embed text using either local or remote backend."""
    mode = _mode or _get_mode()
    if mode == "remote":
        return _remote_embed(text)
    return _local_embed(text)


def _local_embed(text: str) -> list[float]:
    if _local_model is None:
        raise RuntimeError("No local embedding model loaded.")
    result = _local_model.embed(f"search_query: {text}")
    return result[0] if isinstance(result[0], list) else result


def _remote_embed(text: str) -> list[float]:
    api_url = os.getenv("EMBED_API_URL")
    api_key = os.getenv("EMBED_API_KEY", "")
    model_name = os.getenv("EMBED_MODEL_NAME", "nomic-embed-text")

    if not api_url:
        raise RuntimeError("EMBED_API_URL not set.")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    r = requests.post(
        f"{api_url.rstrip('/')}/embeddings",
        headers=headers,
        json={"model": model_name, "input": f"search_query: {text}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["data"][0]["embedding"]
