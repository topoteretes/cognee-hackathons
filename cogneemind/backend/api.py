"""CogneeMind API — FastAPI + WebSocket.

Endpoints:
  GET  /state            current plan + wiki timeline/index + brain status
  POST /scenario/{stage} apply a demo disruption (base|new_flight|gate_closed|storm) and heal
  POST /chat             natural-language interaction (add flight / close gate / storm / query)
  POST /reset            cold-start the world + wiki
  POST /lint             run the wiki linter
  GET  /compounding      cold-vs-warm A/B numbers (the headline evidence)
  WS   /events           live agent-activity stream
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import agents as A
import disruptions as D
import simulator as S
from brain import brain
from chat_intent import extract_intent
from memory import LocalWiki

app = FastAPI(title="CogneeMind")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --------------------------------------------------------------------------- #
# World + wiki state
# --------------------------------------------------------------------------- #
@dataclass
class World:
    flights: list = field(default_factory=S.load_flights)
    gates: list = field(default_factory=S.load_gates)
    plan: dict | None = None
    signature: str = "base"


wiki = LocalWiki()
world = World()


def reset_world(cold_wiki: bool = True):
    global world
    world = World()
    if cold_wiki:
        wiki.reset()


# --------------------------------------------------------------------------- #
# WebSocket connection manager + event streaming
# --------------------------------------------------------------------------- #
class Hub:
    def __init__(self):
        self.conns: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.conns.append(ws)

    def drop(self, ws: WebSocket):
        if ws in self.conns:
            self.conns.remove(ws)

    async def broadcast(self, payload: dict):
        for ws in list(self.conns):
            try:
                await ws.send_json(payload)
            except Exception:
                self.drop(ws)


hub = Hub()


async def stream_events(events: list[dict], result: dict):
    """Replay collected agent events over WS with a small delay, then push the
    final plan + wiki — so the frontend animates the agents 'thinking'."""
    for ev in events:
        await hub.broadcast({"type": "agent", **ev})
        await asyncio.sleep(0.18)
    await hub.broadcast({"type": "plan", "plan": result.get("plan"),
                         "discovery": result.get("discovery"),
                         "wiki_version": result.get("wiki_version")})
    await hub.broadcast({"type": "wiki", "timeline": wiki.history(), "index": wiki.index()})


def run_optimize(signature: str) -> dict:
    """Run the agent loop synchronously, collecting events for streaming."""
    events: list[dict] = []

    def emit(agent, message, data):
        events.append({"agent": agent, "message": message, "data": data, "ts": time.time()})

    result = A.optimize(world.flights, world.gates, signature, wiki,
                        prev_plan=world.plan, emit=emit)
    world.plan = result["plan"]
    world.signature = signature
    return {"result": result, "events": events}


async def optimize_and_stream(signature: str) -> dict:
    out = run_optimize(signature)
    result, events = out["result"], out["events"]
    asyncio.create_task(stream_events(events, result))
    # Mirror to Cognee (judged loop) in the background — never blocks the demo.
    if result.get("discovery"):
        asyncio.create_task(_cognee_mirror(signature, result))
    return {"plan": result["plan"], "discovery": result.get("discovery"),
            "verdict": result.get("verdict"), "wiki_version": result.get("wiki_version"),
            "events": events}


async def _cognee_mirror(signature: str, result: dict):
    disc = result["discovery"]
    sid = f"run-{signature}-{int(time.time())}"
    await brain.remember_trial(signature, disc["strategy"]["name"], disc["score"], sid)
    await brain.distill(signature, disc["strategy"], disc["score"])
    # Grade the prior FAILURE that triggered re-research (low success -> proposal),
    # not the healed plan. Falls back to the healed score for cold/base runs.
    graded = result.get("fail_score") or result["plan"]["score"]
    imp = await brain.self_improve(signature, disc["strategy"], graded, sid)
    await hub.broadcast({"type": "agent", "agent": "brain",
                         "message": f"cognee self-improve (graded penalty {graded['total']}): {imp}",
                         "data": imp, "ts": time.time()})


# --------------------------------------------------------------------------- #
# Scenarios
# --------------------------------------------------------------------------- #
# Scenario buttons apply ONE disruption to a fresh base schedule (non-cumulative),
# so each stage cleanly shows the brain healing. `prev` is the current plan, so the
# R term measures churn vs. base. (Chat disruptions stay freeform/cumulative.)
def _base_plan():
    return S.public_plan(S.assign(S.load_flights(), S.load_gates(), S.default_strategy()))


SCENARIOS = {
    "base": lambda: ("base", World()),
    "new_flight": lambda: (
        D.signature("new_flight", window="busy"),
        World(flights=D.add_flight(S.load_flights(), id="ZZ999", airline="ZetaAir",
                                   arrival="08:30", departure="10:00", type="domestic",
                                   preferred=["G1", "G2"]), gates=S.load_gates())),
    "gate_closed": lambda: (
        D.signature("gate_closed", where="central"),
        World(flights=S.load_flights(), gates=D.close_gate(S.load_gates(), "G3", "08:00", "13:00"))),
    "storm": lambda: (
        D.signature("delay", weather="storm", severity="heavy"),
        World(flights=D.apply_delays(S.load_flights(), ["CD201", "GH401", "IJ501", "CD202"], 30),
              gates=S.load_gates())),
}


@app.post("/scenario/{stage}")
async def scenario(stage: str):
    global world
    if stage not in SCENARIOS:
        return {"error": f"unknown stage '{stage}'", "stages": list(SCENARIOS)}
    if stage == "base":
        reset_world(cold_wiki=False)
        sig, neww = SCENARIOS[stage]()
        world = neww  # base: prev=None -> Researcher discovers the opening plan
        return await optimize_and_stream(sig)
    sig, neww = SCENARIOS[stage]()
    neww.plan = world.plan if world.plan else _base_plan()  # prev plan -> measures churn (R)
    world = neww
    return await optimize_and_stream(sig)


# --------------------------------------------------------------------------- #
# Chat — LLM-first intent parser, rule fallback (see chat_intent.py)
# --------------------------------------------------------------------------- #
class ChatMsg(BaseModel):
    text: str


HELP_TEXT = (
    "I take messy ops chatter and turn it into actions. Try:\n"
    "  • delay AB104 by 1 hr     • close G3       • reopen G3\n"
    "  • add flight 09:15 to G2  • move AB104 to G2\n"
    "  • storm                   • new day        • reset / lint\n"
    "  • what is the best strategy?"
)


def _flight_id_list() -> list[str]:
    return [f.id for f in world.flights]


def _gate_id_list() -> list[str]:
    return [g.id for g in world.gates]


def _resolve_close_window(intent: dict) -> tuple[str, str]:
    """Pick a meaningful close window. If the user gave one, use it; otherwise
    derive it from the LIVE schedule — span = first arrival to last departure
    (+buffer) — so 'G4 is closed' means closed for the whole operational day,
    not a hardcoded 08:00–13:00 fiction. Always returns a non-degenerate window."""
    s = (intent.get("start") or "").strip()
    e = (intent.get("end") or "").strip()
    if s and e and S.hhmm_to_min(s) < S.hhmm_to_min(e):
        return s, e
    if world.flights:
        start_min = min(f.arrival for f in world.flights)
        end_min = max(f.departure for f in world.flights) + S.BUFFER_MIN
        return S.min_to_hhmm(start_min), S.min_to_hhmm(end_min)
    # No flights at all — fall back to a generic ops day.
    return "06:00", "23:00"


def _summarize_optimize(out: dict) -> str:
    """One human line summarizing what the optimize loop just produced."""
    plan = out.get("plan") or {}
    sc = plan.get("score") or {}
    disc = out.get("discovery") or {}
    strat = (disc.get("strategy") or {}).get("name") or plan.get("strategy", {}).get("name") or "existing"
    bits = [f"score {sc.get('total', '?')}",
            f"U={sc.get('U', 0)} C={sc.get('C', 0)} W={sc.get('W', 0)} R={sc.get('R', 0)}",
            f"strategy '{strat}'"]
    if disc:
        bits.append(f"{disc.get('source', 'cold')}, {disc.get('evals', 0)} evals")
    return " · ".join(bits)


def _condense_recall(ans: str | None) -> str:
    """Trim Cognee recall to a short citation tail."""
    if not ans:
        return ""
    s = ans.strip().strip('"').strip("'")
    if len(s) > 240:
        s = s[:237].rstrip() + "…"
    return f'  [cognee: "{s}"]'


@app.post("/chat")
async def chat(msg: ChatMsg):
    global world
    text = (msg.text or "").strip()
    if not text:
        return {"reply": HELP_TEXT, "plan": world.plan}

    intent = await extract_intent(text, _flight_id_list(), _gate_id_list())
    action = intent.get("action")

    # --- world-only commands ------------------------------------------------ #
    if action == "reset":
        reset_world(cold_wiki=True)
        world.plan = S.public_plan(S.assign(world.flights, world.gates, S.default_strategy()))
        return {"reply": "Reset: fresh schedule, cold wiki. The brain has forgotten everything.",
                "plan": world.plan, "discovery": None}

    if action == "new_day":
        # Keep the wiki (memory survives), reset the world to the base schedule.
        world = World()
        world.plan = S.public_plan(S.assign(world.flights, world.gates, S.default_strategy()))
        return {"reply": "New day: schedule reset to base. Wiki memory kept — the brain "
                         f"still remembers {len(wiki.history())} learned strategies.",
                "plan": world.plan, "discovery": None}

    if action == "lint":
        summary = wiki.lint()
        return {"reply": f"Linted the wiki: pruned {summary['pruned_winners']} superseded "
                         f"winner(s) and {summary['pruned_library']} orphan strategy entries.",
                "wiki": {"timeline": wiki.history(), "index": wiki.index()}}

    if action == "help":
        return {"reply": HELP_TEXT, "plan": world.plan}

    # --- disruptions -> re-optimize ----------------------------------------- #
    if action == "delay":
        fid = intent["flight"]
        mins = intent["minutes"]
        world.flights = D.delay_flight(world.flights, fid, mins)
        sig = D.signature("delay", flight=fid, minutes=str(mins))
        out = await optimize_and_stream(sig)
        return {"reply": f"{fid} delayed +{mins} min → re-optimized: {_summarize_optimize(out)}",
                **out}

    if action == "close":
        gid = intent["gate"]
        start, end = _resolve_close_window(intent)
        world.gates = D.close_gate(world.gates, gid, start, end)
        out = await optimize_and_stream(D.signature("gate_closed", where=gid))
        return {"reply": f"{gid} closed {start}–{end} (operational window). "
                         f"Observer flagged it → {_summarize_optimize(out)}", **out}

    if action == "open":
        gid = intent["gate"]
        world.gates = D.open_gate(world.gates, gid)
        out = await optimize_and_stream(D.signature("gate_opened", where=gid))
        return {"reply": f"{gid} reopened → {_summarize_optimize(out)}", **out}

    if action == "add":
        arr = intent["arrival"]
        dep = intent.get("departure") or arr
        gate = intent.get("gate")
        new_id = "NEW" + str(len([f for f in world.flights if f.id.startswith("NEW")]) + 1)
        world.flights = D.add_flight(
            world.flights, id=new_id, airline="AdHoc", arrival=arr, departure=dep,
            type="domestic", preferred=[gate] if gate else ["G1", "G2"])
        out = await optimize_and_stream(D.signature("new_flight", window="busy"))
        gate_note = f" (preferring {gate})" if gate else ""
        return {"reply": f"Added {new_id} arriving {arr}{gate_note} → "
                         f"{_summarize_optimize(out)}", **out}

    if action == "move":
        fid, gid = intent["flight"], intent["gate"]
        world.flights = D.move_flight(world.flights, fid, gid)
        out = await optimize_and_stream(D.signature("move", flight=fid, where=gid))
        return {"reply": f"Moving {fid} → {gid}. Re-optimized: {_summarize_optimize(out)}",
                **out}

    if action == "storm":
        mins = intent.get("minutes", 30)
        world.flights = D.apply_delays(world.flights, ["CD201", "GH401", "IJ501", "CD202"], mins)
        out = await optimize_and_stream(D.signature("delay", weather="storm", severity="heavy"))
        return {"reply": f"Storm applied: international arrivals +{mins} min → "
                         f"{_summarize_optimize(out)}", **out}

    # --- query / unknown: clean wiki + cognee answer ------------------------ #
    hist = wiki.history()
    best = hist[-1] if hist else None
    cognee_ans = await brain.recall_priors(world.signature)
    if best is None:
        base = "No strategy learned yet — trigger a disruption first (e.g. 'close G3', 'storm')."
    else:
        base = (f"Best for '{best['signature']}' → '{best['strategy']}' (score {best['score']}). "
                f"The wiki holds {len(hist)} learned version(s).")
    if action == "unknown":
        base = f"Didn't catch that. {HELP_TEXT}\n\n{base}"
    return {"reply": base + _condense_recall(cognee_ans), "plan": world.plan}


# --------------------------------------------------------------------------- #
# State / wiki / lint / compounding
# --------------------------------------------------------------------------- #
@app.get("/state")
async def state():
    if world.plan is None:
        world.plan = S.public_plan(S.assign(world.flights, world.gates, S.default_strategy()))
    return {"plan": world.plan, "signature": world.signature,
            "wiki": {"timeline": wiki.history(), "index": wiki.index()},
            "brain": {"enabled": brain.enabled, "ready": brain.ready, "skills": brain.skill_names}}


@app.post("/reset")
async def reset():
    reset_world(cold_wiki=True)
    world.plan = S.public_plan(S.assign(world.flights, world.gates, S.default_strategy()))
    return {"ok": True, "plan": world.plan}


@app.post("/lint")
async def lint():
    return {"summary": wiki.lint(), "wiki": {"timeline": wiki.history(), "index": wiki.index()}}


@app.get("/compounding")
async def compounding():
    """Headline evidence: same storm, cold wiki vs warm wiki."""
    tmp = LocalWiki(path=wiki.path.parent / "wiki_ab.json")
    tmp.reset()
    gates = S.load_gates()
    storm = D.apply_delays(S.load_flights(), ["CD201", "GH401", "IJ501", "CD202"], 30)
    sig = D.signature("delay", weather="storm", severity="heavy")

    cold = A.researcher_discover(storm, gates, sig, tmp, budget=2)
    cold_full = A.researcher_discover(storm, gates, sig, tmp)  # full-budget cold to seed wiki
    tmp.promote(sig, cold_full.strategy, cold_full.dead_ends, cold_full.plan["score"]["total"], "seed")
    warm = A.researcher_discover(storm, gates, sig, tmp, budget=2)
    return {
        "scenario": sig,
        "budget": 2,
        "cold": {"score": cold.plan["score"]["total"], "evals": cold.evals,
                 "tried": [t["name"] for t in cold.trace]},
        "warm": {"score": warm.plan["score"]["total"], "evals": warm.evals,
                 "tried": [t["name"] for t in warm.trace]},
        "full_budget": {"cold_evals": cold_full.evals,
                        "cold_score": cold_full.plan["score"]["total"]},
    }


@app.websocket("/events")
async def events(ws: WebSocket):
    await hub.connect(ws)
    try:
        await ws.send_json({"type": "hello", "msg": "CogneeMind event stream connected"})
        while True:
            await ws.receive_text()  # keepalive; we don't expect client messages
    except WebSocketDisconnect:
        hub.drop(ws)
    except Exception:
        hub.drop(ws)


@app.on_event("startup")
async def _startup():
    # Never let a Cognee failure (e.g. a leftover process holding the graph DB
    # lock) crash the demo — degrade to local-only and keep serving.
    try:
        status = await brain.setup()
    except Exception as e:
        brain.enabled = False
        brain.ready = False
        status = (f"cognee setup failed ({type(e).__name__}: {str(e)[:120]}) — "
                  f"running local-only. Tip: kill leftover `uvicorn api:app` processes.")
    print("[CogneeMind]", status)


@app.get("/")
async def root():
    return {"service": "CogneeMind", "stages": list(SCENARIOS),
            "brain_enabled": brain.enabled}
