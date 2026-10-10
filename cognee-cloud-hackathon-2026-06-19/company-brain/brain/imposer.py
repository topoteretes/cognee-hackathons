from pathlib import Path
from brain.ledger import write_receipt

def _corrective(decision, as_of: str) -> str | None:
    """The resolved truth, written back to memory so recall reflects the lint
    decision. forget() is coarse/unreliable on the cloud, so instead of deleting
    the losing fact we re-state the winner authoritatively and explicitly
    deprecate the loser — giving recall a strong, recent, unambiguous signal."""
    d = decision
    w, l = d.winner, d.loser
    if d.action in ("override", "merge") and w is not None:
        base = w.text
        if l is not None:
            base += f" This is the CURRENT, authoritative value as of {as_of}; it supersedes the earlier '{l.value}' ({l.source})."
        return base
    if d.action == "hold" and w is not None and l is not None:
        return (f"BINDING POLICY (authoritative as of {as_of}): {w.text} "
                f"The alternative '{l.value}' proposed via {l.source} is NOT permitted "
                f"and must not be used.")
    if d.action == "retire" and l is not None:
        return (f"RETIRED / OUTDATED as of {as_of}: '{l.value}' ({l.source}, {l.date}) "
                f"is no longer current and must not be used as the answer.")
    return None

async def impose(client, decision, name: str, as_of: str, md: Path, jl: Path) -> dict:
    rec = write_receipt(decision, as_of, md, jl)
    # Enact the decision on the graph by writing the resolved truth back to memory.
    # Hard 'hold' never deletes the policy — it reasserts it and flags the loser.
    corrective = _corrective(decision, as_of)
    if corrective is not None:
        await client.remember(corrective, dataset_name=name, self_improvement=False)
    return rec
