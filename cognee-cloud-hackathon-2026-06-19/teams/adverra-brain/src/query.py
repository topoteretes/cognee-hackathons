"""Query — answer a question from the brain, with a confidence/escalation gate.

Uses Cognee's AGENTIC_COMPLETION search over the knowledge graph. If the brain
returns nothing usable, we report low confidence so the Slack layer can escalate
to a human expert instead of guessing.

Run:
    python -m src.query "How long do PayPal withdrawals take?"
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass

import cognee
from cognee import SearchType

from .brain import DATASET, connect_cloud_if_configured

# Phrases that signal the brain/agent decided it cannot answer from stored
# knowledge. Matched after normalizing typographic apostrophes/quotes to ASCII.
_NO_ANSWER_MARKERS = (
    "don't have",
    "do not have",
    "doesn't have",
    "does not have",
    "no confident answer",
    "not in the",
    "cannot find",
    "can't find",
    "couldn't find",
    "could not find",
    "can't confirm",
    "cannot confirm",
    "no relevant information",
    "don't know",
    "do not know",
    "no stored",
    "not stored",
    "isn't in the knowledge",
    "not in the knowledge",
    "no information",
    "no record",
    "no article",
)


def _normalize(text: str) -> str:
    """Fold typographic quotes/apostrophes to ASCII so markers match."""
    return (
        text.replace("’", "'")
        .replace("‘", "'")
        .replace("“", '"')
        .replace("”", '"')
    )


@dataclass
class Answer:
    text: str
    confident: bool
    raw: object = None


def _to_text(result) -> str:
    """Normalize Cognee search output (list / dict / str) to a string."""
    if result is None:
        return ""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, (list, tuple)):
        parts = [_to_text(r) for r in result]
        return "\n".join(p for p in parts if p).strip()
    if isinstance(result, dict):
        for key in ("search_result", "answer", "text", "content", "result"):
            if result.get(key):
                return _to_text(result[key])
        return str(result).strip()
    return str(result).strip()


def _is_confident(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    stripped = text.strip()
    # The qa-answerer skill emits this token when the brain has no direct answer.
    if stripped.upper().startswith("ESCALATE"):
        return False
    low = _normalize(stripped).lower()
    return not any(marker in low for marker in _NO_ANSWER_MARKERS)


def escalation_reason(text: str) -> str | None:
    """If the answer is an ESCALATE token, return its reason; else None."""
    stripped = (text or "").strip()
    if stripped.upper().startswith("ESCALATE"):
        return stripped.split(":", 1)[1].strip() if ":" in stripped else ""
    return None


_JUDGE_SYSTEM = (
    "You grade a support-bot answer for the company Cashly. You decide whether "
    "the answer actually resolves the user's question using SPECIFIC documented "
    "Cashly facts (concrete numbers, named policies, exact steps), versus an "
    "answer that admits it lacks the info or only offers generic advice such as "
    "'contact support', 'check the app', or offering to draft a message.\n"
    "Reply with strict JSON: {\"grounded\": true|false}. "
    "grounded=true ONLY if the answer contains specific, documented Cashly facts "
    "that directly answer the question. If it is generic, speculative, hedged, or "
    "admits missing information, grounded=false."
)


async def _judge_grounded(question: str, answer: str) -> bool:
    """LLM-as-judge confidence gate. Falls back to the keyword heuristic on error."""
    try:
        import os

        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.environ["LLM_API_KEY"].strip())
        resp = await client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user",
                 "content": f"Question:\n{question}\n\nAnswer:\n{answer}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=20,
        )
        import json

        return bool(json.loads(resp.choices[0].message.content).get("grounded"))
    except Exception as exc:
        print(f"[query] judge unavailable ({exc}); using keyword heuristic.")
        return _is_confident(answer)


async def ask(question: str, session_id: str | None = None,
              skills: list[str] | None = None) -> Answer:
    """Ask the brain a question. session_id keeps working memory per-conversation."""
    await connect_cloud_if_configured()

    kwargs = dict(
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=[DATASET],
        max_iter=6,
    )
    if skills:
        kwargs["skills"] = skills
    if session_id:
        kwargs["session_id"] = session_id

    steered = (
        f"{question}\n\n"
        "[Answer directly and concisely using the documented Cashly facts in the "
        "knowledge base. Give the specific numbers/steps. Do NOT ask the user "
        "clarifying questions. If the knowledge base truly has nothing on this, "
        "say so plainly in one sentence.]"
    )
    result = await cognee.search(steered, **kwargs)
    text = _to_text(result)
    return Answer(text=text, confident=_is_confident(text), raw=result)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How long do PayPal withdrawals take?"
    ans = asyncio.run(ask(q))
    print(f"\nQ: {q}")
    print(f"confident: {ans.confident}\n")
    print(ans.text or "(empty)")
