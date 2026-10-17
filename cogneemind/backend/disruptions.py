"""Disruption injectors + disruption-signature for the wiki index.

A disruption mutates the flight/gate world. Applied on top of an existing
assignment it can produce a *stale* plan with conflicts/unassigned flights —
which the Observer detects and the Researcher then heals.
"""
from __future__ import annotations

from simulator import Flight, Gate, hhmm_to_min


def add_flight(flights: list[Flight], *, id: str, airline: str, arrival: str,
               departure: str, type: str = "domestic", preferred=None) -> list[Flight]:
    flights = list(flights)
    flights.append(Flight(id, airline, hhmm_to_min(arrival), hhmm_to_min(departure),
                          type, list(preferred or [])))
    return flights


def close_gate(gates: list[Gate], gate_id: str, start: str, end: str) -> list[Gate]:
    gates = [Gate(g.id, g.position, g.type, g.terminal, g.label, list(g.closed_windows)) for g in gates]
    for g in gates:
        if g.id == gate_id:
            g.closed_windows.append((hhmm_to_min(start), hhmm_to_min(end)))
    return gates


def apply_delays(flights: list[Flight], ids: list[str], minutes: int) -> list[Flight]:
    out = []
    for f in flights:
        if f.id in ids:
            out.append(Flight(f.id, f.airline, f.arrival + minutes, f.departure + minutes,
                              f.type, list(f.preferred), delay=f.delay + minutes))
        else:
            out.append(f)
    return out


def delay_flight(flights: list[Flight], flight_id: str, minutes: int) -> list[Flight]:
    """Delay a single flight by `minutes` (negative = pull earlier)."""
    return apply_delays(flights, [flight_id], minutes)


def open_gate(gates: list[Gate], gate_id: str) -> list[Gate]:
    """Re-open a gate by clearing its closed windows."""
    out = [Gate(g.id, g.position, g.type, g.terminal, g.label, list(g.closed_windows)) for g in gates]
    for g in out:
        if g.id == gate_id:
            g.closed_windows = []
    return out


def move_flight(flights: list[Flight], flight_id: str, gate_id: str) -> list[Flight]:
    """Pin a flight's preference to a single gate so the next assignment
    places it there if feasible (falls back to other gates otherwise)."""
    out = []
    for f in flights:
        if f.id == flight_id:
            out.append(Flight(f.id, f.airline, f.arrival, f.departure, f.type,
                              [gate_id], delay=f.delay))
        else:
            out.append(f)
    return out


def signature(kind: str, **meta) -> str:
    """Short, recall-friendly disruption signature used as the wiki index key.

    e.g. 'delay:storm:heavy', 'gate_closed:central', 'new_flight:busy_window'.
    The Researcher recalls past winning strategies by this signature.
    """
    tags = ":".join(str(v) for v in meta.values() if v is not None)
    return f"{kind}:{tags}" if tags else kind
