import json
from pathlib import Path
from brain.facts import load_facts
from brain.config import ROOT, normalize_source

async def ingest_facts(client, name: str) -> int:
    facts = load_facts(name)
    for f in facts:
        await client.remember(
            f.text, dataset_name=name,
            node_set=[name, normalize_source(f.source)],
            self_improvement=False,
        )
    await client.cognify(datasets=name)
    return len(facts)

def _slack_to_text(path: Path) -> str:
    msgs = json.loads(path.read_text())
    return "\n".join(f'{m.get("user","?")}: {m.get("text","")}' for m in msgs)

async def ingest_documents(client, name: str) -> int:
    base = ROOT / "data" / name
    count = 0
    for p in base.rglob("*"):
        if p.suffix in (".md", ".txt"):
            await client.add(p.read_text(), dataset_name=f"{name}_docs"); count += 1
        elif p.suffix == ".json" and "slack" in str(p):
            await client.add(_slack_to_text(p), dataset_name=f"{name}_docs"); count += 1
        # .pdf / .docx -> text via the liteparse skill (the implementing agent runs liteparse,
        # writes <file>.txt next to the source, which the .txt branch above then ingests)
    await client.cognify(datasets=f"{name}_docs")
    return count
