# CogneeMind — Gate Assignment Rulebook

This is the durable rulebook for the Airport Gate-Ops Brain. Hard rules are
never broken; soft goals are optimization targets that the score trades off.

## Hard rules (never violated)

1. **Gate capacity** — a gate serves at most one flight at a time. A flight
   occupies its gate from arrival to departure, plus a **15-minute buffer**
   afterwards for turnaround/cleaning.
2. **One gate per flight** — every flight is assigned to exactly one gate, or
   explicitly flagged "no gate" (remote stand / bus boarding).
3. **Compatibility** — a flight may only use a gate whose `type` accepts it.
   `domestic` gates take domestic flights, `international` gates take
   international flights, `both` gates take either.

## Soft goals (minimize, weighted in the score)

- **Passenger walking** — prefer assigning a flight to one of its `preferred`
  gates; penalty grows with distance (gate `position`) from the nearest
  preferred gate.
- **Operational stability** — avoid changing a flight's gate between plans;
  each reassignment is penalized.

## Score (lower is better)

```
Score = 1000*U + 500*C + 1*W + 5*R
```

- `U` = flights with no gate (remote stand)
- `C` = gate conflicts (overlapping flights on one gate)
- `W` = total walking penalty (distance from preferred gates)
- `R` = reassignments vs the previous plan

Missing gates and conflicts are catastrophic; walking is mildly bad; churn is
penalized so the plan stays stable for staff.
