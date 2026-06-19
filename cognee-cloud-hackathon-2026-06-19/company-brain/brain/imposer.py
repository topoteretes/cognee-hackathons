from pathlib import Path
from brain.ledger import write_receipt

async def impose(client, decision, name: str, as_of: str, md: Path, jl: Path) -> dict:
    rec = write_receipt(decision, as_of, md, jl)
    # Enact on the graph. forget() by dataset+everything is coarse; for the demo we
    # re-state the winner so recall favors it, and (for retire) we record the removal
    # in receipts. Hard 'hold' never deletes the policy.
    if decision.action in ("override", "merge") and decision.winner is not None:
        await client.remember(decision.winner.text, dataset_name=name, self_improvement=False)
    return rec
