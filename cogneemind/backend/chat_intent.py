"""Chat intent extraction for the Ops Console.

Two-stage pipeline:
  1. LLM-first   — uses the OpenAI client (already a cognee dep) with the same
                   LLM_API_KEY the brain uses, returns a strict JSON action.
  2. Rule fallback — typo-tolerant regex parser. Always runs if the LLM is
                   unavailable, errors, returns garbage, or names an entity
                   that doesn't exist in the live world.

Returned `Intent` is a flat dict the api.py dispatcher consumes:

    {"action": "delay",     "flight": "AB104", "minutes": 60}
    {"action": "close",     "gate": "G3", "start": "08:00", "end": "13:00"}
    {"action": "open",      "gate": "G3"}
    {"action": "add",       "arrival": "09:15", "departure": "10:15", "gate": "G2" | None}
    {"action": "move",      "flight": "AB104", "gate": "G2"}
    {"action": "storm",     "minutes": 30}
    {"action": "new_day"}
    {"action": "reset"}
    {"action": "lint"}
    {"action": "help"}
    {"action": "query",     "text": "<original>"}
    {"action": "unknown",   "text": "<original>"}
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# Helpers shared by both paths
# --------------------------------------------------------------------------- #
ACTIONS = {
    "delay", "close", "open", "add", "move", "storm",
    "new_day", "reset", "lint", "help", "query",
}

_DUR_UNITS = {
    "h": 60, "hr": 60, "hrs": 60, "hour": 60, "hours": 60,
    "m": 1, "min": 1, "mins": 1, "minute": 1, "minutes": 1,
}
_TIME_RE = re.compile(r"\b(\d{1,2})[:h](\d{2})\b")
_DUR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b", re.I)
_FLIGHT_RE = re.compile(r"\b([A-Z]{2}\s?\d{2,4})\b")
_GATE_RE = re.compile(r"\b(g\s?\d{1,2})\b", re.I)


def _normalize_flight(s: str) -> str:
    return s.replace(" ", "").upper()


def _normalize_gate(s: str) -> str:
    return s.replace(" ", "").upper()


def _parse_minutes(text: str) -> Optional[int]:
    """Best-effort duration: '1 hr', '40 mins', '1h30m', 'an hour', 'half an hour'."""
    text = text.lower()
    # check 'half an hour' BEFORE 'an hour' so the half-prefix wins
    if re.search(r"\bhalf\s+(an\s+)?hour\b", text):
        return 30
    if re.search(r"\b(an?|one)\s+hour\b", text):
        return 60
    total = 0
    for n, u in _DUR_RE.findall(text):
        u = u.lower()
        mult = _DUR_UNITS.get(u, _DUR_UNITS.get(u.rstrip("s"), 1))
        total += int(float(n) * mult)
    return total or None


def _parse_time(text: str) -> Optional[str]:
    m = _TIME_RE.search(text)
    if not m:
        return None
    h, mn = int(m.group(1)), int(m.group(2))
    if 0 <= h < 24 and 0 <= mn < 60:
        return f"{h:02d}:{mn:02d}"
    return None


def _bump_hhmm(t: str, minutes: int) -> str:
    h, m = t.split(":")
    total = int(h) * 60 + int(m) + minutes
    total %= 24 * 60
    return f"{total // 60:02d}:{total % 60:02d}"


def _hhmm_min(t: str) -> int:
    """Convert HH:MM to minutes-since-midnight; defensive on garbage input."""
    try:
        h, m = t.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return -1


# --------------------------------------------------------------------------- #
# World-aware validation: fixes typos by matching against live IDs
# --------------------------------------------------------------------------- #
def _resolve_flight(raw: str, flight_ids: list[str]) -> Optional[str]:
    if not raw:
        return None
    target = _normalize_flight(raw)
    if target in flight_ids:
        return target
    # tolerate a single edit: AB10 vs AB104, AB1O4 vs AB104, etc.
    for fid in flight_ids:
        if _close_enough(target, fid, max_edits=1):
            return fid
    return None


def _resolve_gate(raw: str, gate_ids: list[str]) -> Optional[str]:
    if not raw:
        return None
    target = _normalize_gate(raw)
    if target in gate_ids:
        return target
    if _close_enough(target, "G" + target.lstrip("G"), max_edits=0):
        # already handled above; this just keeps the symmetry simple
        pass
    for gid in gate_ids:
        if _close_enough(target, gid, max_edits=1):
            return gid
    return None


def _close_enough(a: str, b: str, max_edits: int = 1) -> bool:
    if a == b:
        return True
    if abs(len(a) - len(b)) > max_edits:
        return False
    # Levenshtein with early exit; tiny strings, fine to be naive.
    n, m = len(a), len(b)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        cur = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        if min(cur) > max_edits:
            return False
        prev = cur
    return prev[m] <= max_edits


# --------------------------------------------------------------------------- #
# Rule-based parser (deterministic fallback / "no LLM" mode)
# --------------------------------------------------------------------------- #
_DELAY_STEMS = ("delay", "delaz", "deal", "late", "push", "slip", "slip ")
_CLOSE_STEMS = ("clos", "cls", "shut", "block")  # 'cls' tolerates 'clsoed'/'clsed' typos
_OPEN_STEMS = ("open", "reopen", "unblock", "restore")
_ADD_STEMS = ("add", "new flight", "insert", "schedul")
_MOVE_STEMS = ("move", "swap", "reassign", "shift to", "send to")
_STORM_STEMS = ("storm", "weather", "cascading")
_NEW_DAY = ("new day", "fresh day", "fresh schedule", "tomorrow", "rollover")
_HELP_STEMS = ("help", "what can you", "how do i")


def parse_rules(text: str, flight_ids: list[str], gate_ids: list[str]) -> dict:
    """Deterministic parser. Always returns a valid Intent dict."""
    raw = text.strip()
    t = raw.lower()

    if not t:
        return {"action": "unknown", "text": raw}

    if any(s in t for s in _NEW_DAY):
        return {"action": "new_day"}
    if "reset" in t:
        return {"action": "reset"}
    if "lint" in t:
        return {"action": "lint"}
    if any(s in t for s in _HELP_STEMS):
        return {"action": "help"}

    fmatch = _FLIGHT_RE.search(raw.upper())
    flight_raw = fmatch.group(1) if fmatch else None
    flight = _resolve_flight(flight_raw, flight_ids) if flight_raw else None

    gates_in_text = [_resolve_gate(m.group(1), gate_ids) for m in _GATE_RE.finditer(raw)]
    gates_in_text = [g for g in gates_in_text if g]
    gate = gates_in_text[0] if gates_in_text else None

    minutes = _parse_minutes(t)
    time_str = _parse_time(t)

    # CLOSE / OPEN gate
    if gate and any(s in t for s in _OPEN_STEMS):
        return {"action": "open", "gate": gate}
    if gate and any(s in t for s in _CLOSE_STEMS):
        out: dict[str, Any] = {"action": "close", "gate": gate}
        # Only attach explicit times if the user actually wrote a window
        # ("from HH:MM to HH:MM"); otherwise let the dispatcher derive it.
        m_range = re.search(r"(\d{1,2}:\d{2})\s*(?:to|-|until|till|–)\s*(\d{1,2}:\d{2})", t)
        if m_range:
            s, e = m_range.group(1), m_range.group(2)
            if _hhmm_min(s) < _hhmm_min(e):
                out["start"], out["end"] = s, e
        return out

    # DELAY a specific flight
    if flight and (any(s in t for s in _DELAY_STEMS) or minutes):
        return {"action": "delay", "flight": flight, "minutes": minutes or 30}

    # MOVE flight to gate
    if flight and gate and any(s in t for s in _MOVE_STEMS):
        return {"action": "move", "flight": flight, "gate": gate}

    # STORM (delay 4 internationals 30 min — same as the demo button)
    if any(s in t for s in _STORM_STEMS):
        return {"action": "storm", "minutes": minutes or 30}

    # ADD a flight
    if any(s in t for s in _ADD_STEMS):
        arr = time_str or "08:30"
        out: dict[str, Any] = {"action": "add", "arrival": arr,
                               "departure": _bump_hhmm(arr, 60)}
        if gate:
            out["gate"] = gate
        return out

    # Looks like a question (best/strategy/recall/why/what)?
    if any(w in t for w in ("best", "strateg", "recall", "why", "what", "wiki", "memory", "?")):
        return {"action": "query", "text": raw}

    return {"action": "unknown", "text": raw}


# --------------------------------------------------------------------------- #
# LLM parser (primary path when LLM_API_KEY is set)
# --------------------------------------------------------------------------- #
_SYSTEM_PROMPT = """You translate messy airport-ops chatter into a single JSON action.

Schema (return ONE of these, no prose, no code fences):
  {"action":"delay","flight":"<ID>","minutes":<int>}
  {"action":"close","gate":"G<n>","start":"HH:MM","end":"HH:MM"}
  {"action":"open","gate":"G<n>"}
  {"action":"add","arrival":"HH:MM","departure":"HH:MM","gate":"G<n>"|null}
  {"action":"move","flight":"<ID>","gate":"G<n>"}
  {"action":"storm","minutes":<int>}
  {"action":"new_day"}
  {"action":"reset"}
  {"action":"lint"}
  {"action":"help"}
  {"action":"query","text":"<original user text>"}

Rules:
- The user often types with heavy typos: "deallzed bs 40 mins" = delay 40 min,
  "g4 gate is clsoed" = close G4, "ab104 dealz bs 1hr" = delay AB104 60 min.
- Flight IDs and gate IDs MUST be from the lists provided. If you can't match
  one confidently, return action="query".
- For action=close: only set "start"/"end" if the user EXPLICITLY gave times
  ("close G4 from 09:00 to 11:00"). Otherwise OMIT both fields — the server
  will derive the operational window from the live schedule. NEVER fabricate
  "00:00" or any default times yourself.
- For action=delay: minutes MUST be > 0. Default to 30 if unspecified.
- "1 hr"/"an hour" = 60 min. "half an hour" = 30. "40 mins" = 40.
- "storm"/"weather"/"cascading delays" without a flight ID = action=storm.
- "new day"/"tomorrow"/"fresh schedule" = new_day (keeps the wiki).
- If unclear, choose action="query" with the original text — never guess IDs.
- Output ONLY the JSON object. No commentary."""


def _llm_available() -> bool:
    if not os.environ.get("LLM_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        return False
    try:
        import openai  # noqa: F401
        return True
    except Exception:
        return False


async def parse_llm(text: str, flight_ids: list[str], gate_ids: list[str]) -> Optional[dict]:
    """Returns a validated Intent dict, or None on any failure."""
    if not _llm_available():
        return None
    try:
        from openai import AsyncOpenAI
    except Exception:
        return None
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    client = AsyncOpenAI(api_key=api_key)
    user_msg = (
        f"Live flight IDs: {', '.join(flight_ids)}\n"
        f"Live gate IDs: {', '.join(gate_ids)}\n"
        f"User: {text}"
    )
    try:
        resp = await client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            temperature=0,
            timeout=8,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content or "{}"
        data = json.loads(raw)
    except Exception:
        return None

    return _validate(data, text, flight_ids, gate_ids)


def _validate(data: Any, text: str, flight_ids: list[str], gate_ids: list[str]) -> Optional[dict]:
    if not isinstance(data, dict):
        return None
    action = data.get("action")
    if action not in ACTIONS and action != "unknown":
        return None

    if action == "delay":
        flight = _resolve_flight(str(data.get("flight", "")), flight_ids)
        mins = data.get("minutes")
        try:
            mins = int(mins)
        except Exception:
            mins = 30
        if not flight:
            return None
        if mins <= 0:
            mins = 30  # default to a real disruption rather than a no-op
        return {"action": "delay", "flight": flight, "minutes": mins}

    if action == "close":
        gate = _resolve_gate(str(data.get("gate", "")), gate_ids)
        if not gate:
            return None
        out: dict[str, Any] = {"action": "close", "gate": gate}
        # Only carry start/end forward if the user (or LLM) supplied a real,
        # non-degenerate window. Otherwise omit — the dispatcher will derive
        # the closure window from the live schedule.
        start = (data.get("start") or "").strip()
        end = (data.get("end") or "").strip()
        if (_TIME_RE.match(start) and _TIME_RE.match(end)
                and _hhmm_min(start) < _hhmm_min(end)):
            out["start"], out["end"] = start, end
        return out

    if action == "open":
        gate = _resolve_gate(str(data.get("gate", "")), gate_ids)
        if not gate:
            return None
        return {"action": "open", "gate": gate}

    if action == "add":
        arr = data.get("arrival") or "08:30"
        dep = data.get("departure") or _bump_hhmm(arr, 60)
        if not _TIME_RE.match(arr) or not _TIME_RE.match(dep):
            return None
        out: dict[str, Any] = {"action": "add", "arrival": arr, "departure": dep}
        gate = _resolve_gate(str(data.get("gate") or ""), gate_ids)
        if gate:
            out["gate"] = gate
        return out

    if action == "move":
        flight = _resolve_flight(str(data.get("flight", "")), flight_ids)
        gate = _resolve_gate(str(data.get("gate", "")), gate_ids)
        if not (flight and gate):
            return None
        return {"action": "move", "flight": flight, "gate": gate}

    if action == "storm":
        mins = data.get("minutes") or 30
        try:
            mins = int(mins)
        except Exception:
            mins = 30
        return {"action": "storm", "minutes": mins}

    if action in ("new_day", "reset", "lint", "help"):
        return {"action": action}

    if action == "query":
        return {"action": "query", "text": str(data.get("text") or text)}

    return None


# --------------------------------------------------------------------------- #
# Public entry point used by api.py
# --------------------------------------------------------------------------- #
async def extract_intent(text: str, flight_ids: list[str], gate_ids: list[str]) -> dict:
    """LLM-first, rule-fallback. Always returns a valid Intent."""
    intent = await parse_llm(text, flight_ids, gate_ids)
    if intent and intent.get("action") not in (None, "unknown"):
        return intent
    return parse_rules(text, flight_ids, gate_ids)
