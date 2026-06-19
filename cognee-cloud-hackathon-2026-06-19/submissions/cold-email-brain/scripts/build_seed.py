"""Build seed.json = 10 real Gmail emails + ~80 LLM-synthesized examples.

Run once: `python scripts/build_seed.py`
Requires LLM_API_KEY in env (set after kickoff).
"""

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain import config  # noqa: E402


SYNTH_PROMPT = """Du bist ein Trainingsdaten-Generator für eine KI, die lernt, bessere Cold-Outreach-E-Mails an deutsche Handwerker zu schreiben.

Erzeuge GENAU 10 verschiedene Outbound-E-Mails an deutsche Handwerksbetriebe (Dachdecker, Maler, Fliesenleger, Tischler, Elektriker, Sanitär, HVAC, etc.) — jede mit einem realistischen Outcome.

Verteilung der Outcomes:
- 5 ignored (klassische Cold-Mails ohne Antwort)
- 2 declined (höfliche Absage)
- 2 positive_reply (Interesse signalisiert)
- 1 demo_booked (echter Erfolg)

Verteilung der Hooks:
- pain_point_cold
- post_call_followup
- compliment_their_reviews
- mutual_connection
- competitive_humility
- informal_humor

Verteilung der Branchen + Regionen: möglichst divers.

JEDE E-Mail soll eine realistische Länge haben (60-200 Wörter).
JEDE E-Mail soll wirken, als hätte ein echter BDR sie geschrieben — kein KI-Slop.

Antworte AUSSCHLIESSLICH mit einem JSON-Array. Schema pro Eintrag:
{
  "id": "synth-XXX",
  "industry": "string",
  "region": "string",
  "team_size": int,
  "hook_type": "string",
  "called_first": bool,
  "post_call_warm": bool,
  "subject": "string",
  "body": "string (echte deutsche Mail)",
  "outcome": "ignored|declined|positive_reply|demo_booked",
  "score": float 0..1 (passend zum outcome),
  "notes": "1-Satz Insight über das, was funktioniert hat oder nicht"
}

Outcome → Score mapping als Richtschnur:
- ignored → 0.1 - 0.25
- declined → 0.3 - 0.45
- positive_reply → 0.65 - 0.8
- demo_booked → 0.85 - 0.95

Schreibe Outbound-Mails auf dem Niveau eines guten BDRs für ein Handwerker-CRM (HandwerkerCRM). Pain Points: Papierkram nach Feierabend, Aufmaß-Zettel verlieren, Angebote zu langsam rausgeben, Zeiterfassung auf Bauzettel."""


async def generate_synthetic(n_batches: int = 8) -> list[dict]:
    """Call OpenAI to produce 10 examples per batch, n_batches batches → ~80 examples."""
    from openai import AsyncOpenAI

    api_key = config.LLM_API_KEY
    if not api_key:
        raise RuntimeError("LLM_API_KEY not set in env. Export it after kickoff.")

    client = AsyncOpenAI(api_key=api_key)

    async def one_batch(batch_idx: int) -> list[dict]:
        resp = await client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": SYNTH_PROMPT}],
            response_format={"type": "json_object"},
            temperature=0.9,
        )
        text = resp.choices[0].message.content
        # Tolerate {"emails":[...]} or bare array
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                for key in ("emails", "examples", "data", "items"):
                    if key in parsed and isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break
            if not isinstance(parsed, list):
                return []
            # Re-id to avoid collisions across batches
            for i, item in enumerate(parsed):
                item["id"] = f"synth-{batch_idx:02d}-{i:02d}"
            return parsed
        except json.JSONDecodeError:
            print(f"[synth] batch {batch_idx} returned unparseable JSON, skipping")
            return []

    results = await asyncio.gather(*[one_batch(i) for i in range(n_batches)])
    flat = [item for batch in results for item in batch]
    print(f"[synth] generated {len(flat)} synthetic examples")
    return flat


async def main():
    real_path = ROOT / "data" / "real_emails.json"
    if not real_path.exists():
        raise FileNotFoundError("data/real_emails.json missing — corpus extraction must run first.")

    real = json.loads(real_path.read_text())
    print(f"[seed] real corpus: {len(real)} emails")

    synth = await generate_synthetic()

    seed = real + synth
    out = ROOT / "data" / "seed.json"
    out.write_text(json.dumps(seed, ensure_ascii=False, indent=2))
    print(f"[seed] wrote {out} ({len(seed)} total entries)")


if __name__ == "__main__":
    asyncio.run(main())
