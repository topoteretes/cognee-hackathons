"""Critic: score an email across measurable rubric dimensions + propose one concrete fix.

Hybrid scorer:
  1. Local rubric — deterministic, observable features. Fast, reliable.
  2. Cognee-driven critic (optional) — for richer fix_suggestion via the skill.

The hackathon's self-improvement loop is driven by the rubric score being
recorded as a SkillRunEntry. The critic skill itself also evolves via that
loop (its rubric can be rewritten by feedback over time).
"""

import json
import re

import cognee
from cognee import SearchType

from . import config
from ._text import coerce_text as _coerce_text


RUBRIC_WEIGHTS = {
    "trade_specific_pain": 0.30,
    "prior_touchpoint_handling": 0.20,
    "cta_clarity": 0.20,
    "length_discipline": 0.15,
    "tone_match": 0.15,
}


TRADE_PAIN_MARKERS: dict[str, list[str]] = {
    "dachdecker": ["aufmaß", "wetter", "regen", "witterung", "dach", "schiefer", "ziegel"],
    "maler": ["untergrund", "qm", "farbton", "spachtel", "anstrich", "tapete"],
    "fliesen": ["verschnitt", "fugen", "skizze", "qm", "untergrund", "fliesen"],
    "tischler": ["maß", "skizze", "stückliste", "holz", "korpus"],
    "elektriker": ["leitung", "stromkreis", "verteiler", "schaltplan"],
    "sanitär": ["leitung", "rohr", "installation", "bad"],
    "hvac": ["heizlast", "wärmebedarf", "anlage"],
    "wohnbau": ["gewerk", "subunternehmer", "bauleitung"],
    "generalbauer": ["gewerk", "subunternehmer", "bauleitung"],
}


GENERIC_BAD_PHRASES = [
    "bürokram", "viele handwerker, mit denen ich spreche", "papierkram",
    "all-in-one", "digitalisierung", "effizienz",
]


def _score_locally(email: str, prospect: dict) -> dict:
    text = email.lower()
    word_count = len(email.split())

    # Trade-specific pain
    industry_key = next(
        (k for k in TRADE_PAIN_MARKERS if k in (prospect.get("industry") or "").lower()),
        None,
    )
    trade_hits = sum(1 for m in TRADE_PAIN_MARKERS.get(industry_key, []) if m in text) if industry_key else 0
    generic_hits = sum(1 for p in GENERIC_BAD_PHRASES if p in text)
    trade_score = max(0.0, min(RUBRIC_WEIGHTS["trade_specific_pain"], trade_hits * 0.1 - generic_hits * 0.05))

    # Prior touchpoint
    prior_call = bool(prospect.get("prior_call"))
    has_call_ref = any(
        marker in text
        for marker in ["telefonat", "telefonisch", "angerufen", "anruf", "wie versprochen", "wie besprochen"]
    )
    if prior_call:
        touchpoint_score = RUBRIC_WEIGHTS["prior_touchpoint_handling"] if has_call_ref else 0.0
    else:
        # No prior call — reward a specific pattern interrupt instead.
        interrupt_markers = ["hab ihre website", "sterne", "bewertungen", "auf ihrer seite"]
        touchpoint_score = (
            RUBRIC_WEIGHTS["prior_touchpoint_handling"]
            if any(m in text for m in interrupt_markers)
            else 0.05
        )

    # CTA clarity — count number of asks
    cta_count = sum(
        1
        for cue in ["rufen sie", "schauen sie", "buchen sie", "termin", "demo", "callback", "zurück", "vorbei"]
        if cue in text
    )
    cta_score = (
        RUBRIC_WEIGHTS["cta_clarity"] if cta_count <= 2
        else RUBRIC_WEIGHTS["cta_clarity"] * 0.5 if cta_count <= 3
        else 0.05
    )

    # Length discipline
    if word_count <= 100:
        length_score = RUBRIC_WEIGHTS["length_discipline"]
    elif word_count <= 150:
        length_score = RUBRIC_WEIGHTS["length_discipline"] * 0.7
    elif word_count <= 220:
        length_score = RUBRIC_WEIGHTS["length_discipline"] * 0.4
    else:
        length_score = 0.05

    # Tone — punish 5-step explainer template
    bad_template_markers = ["1.", "2.", "3.", "4.", "5.", "schritt", "ins handy sprechen"]
    template_hits = sum(1 for m in bad_template_markers if m in text)
    tone_score = (
        RUBRIC_WEIGHTS["tone_match"] if template_hits <= 1
        else RUBRIC_WEIGHTS["tone_match"] * 0.5 if template_hits <= 3
        else 0.05
    )

    total = round(trade_score + touchpoint_score + cta_score + length_score + tone_score, 3)

    # Fix suggestion picks the lowest-scoring criterion
    breakdown = {
        "trade_specific_pain": round(trade_score, 3),
        "prior_touchpoint_handling": round(touchpoint_score, 3),
        "cta_clarity": round(cta_score, 3),
        "length_discipline": round(length_score, 3),
        "tone_match": round(tone_score, 3),
    }
    weakest = min(breakdown, key=lambda k: breakdown[k] / RUBRIC_WEIGHTS[k])
    fix_map = {
        "trade_specific_pain": f"name {industry_key or 'trade'}-specific pain in the prospect's own vocabulary",
        "prior_touchpoint_handling": (
            "open with explicit reference to the attempted call"
            if prior_call
            else "lead with a specific pattern interrupt (their reviews, website, etc.)"
        ),
        "cta_clarity": "cut to one clear CTA — drop multiple asks",
        "length_discipline": "under 100 words for cold outbound — drop the 5-step product explainer",
        "tone_match": "drop the numbered 5-step template — it reads as copy-paste",
    }
    fix = fix_map.get(weakest, "tighten the email")

    return {
        "score": total,
        "criteria": breakdown,
        "fix_suggestion": fix,
        "word_count": word_count,
        "method": "local-rubric",
    }


async def score_email(
    email: str,
    prospect: dict,
    skill_names: list[str],
    session_id: str,
) -> dict:
    """Score an email. Always uses local rubric (reliable). Also fetches a richer
    fix_suggestion via the Cognee critic skill when available."""
    local = _score_locally(email, prospect)
    try:
        task = (
            "Schlage EINE konkrete, umsetzbare Verbesserung für diese Outbound-Mail vor. "
            "Antworte mit EINEM Satz, kein JSON, keine Aufzählung. "
            "Berücksichtige die Branche und ob vorher angerufen wurde.\n\n"
            f"Prospect: {json.dumps(prospect, ensure_ascii=False)}\n\n"
            f"Email:\n{email}"
        )
        result = await cognee.search(
            task,
            query_type=SearchType.AGENTIC_COMPLETION,
            datasets=[config.DATASET],
            skills=skill_names,
            max_iter=2,
            session_id=session_id,
        )
        cognee_fix = _coerce_text(result).strip()
        if cognee_fix and len(cognee_fix) < 400:
            local["fix_suggestion"] = cognee_fix
            local["method"] = "local-rubric + cognee-fix"
    except Exception as e:
        local["cognee_fix_error"] = str(e)
    return local
