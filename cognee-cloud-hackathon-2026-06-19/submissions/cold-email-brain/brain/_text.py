"""Single robust text extractor for Cognee search results.

Cognee Cloud's `cognee.search(AGENTIC_COMPLETION)` returns shapes like:
    {"dataset_id":..., "search_result": ["the text"]}
or sometimes a list of those dicts, or a bare string. Pull the text reliably.
"""

from typing import Any


def coerce_text(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        sr = result.get("search_result")
        if sr is not None:
            return coerce_text(sr)
        for key in ("content", "text", "message", "answer", "result"):
            if key in result and result[key]:
                return coerce_text(result[key])
        return ""
    if isinstance(result, (list, tuple)):
        parts = [coerce_text(item) for item in result]
        parts = [p for p in parts if p]
        return parts[0] if parts else ""
    return str(result).strip()
