"""Environment + constants. Loads .env if present, otherwise reads OS env."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass


ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "my_skills"
SEED_PATH = ROOT / "data" / "seed.json"

DATASET = "cold-email-brain"

COGNEE_CLOUD_URL = os.environ.get("COGNEE_CLOUD_URL")
COGNEE_API_KEY = os.environ.get("COGNEE_API_KEY")
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-4o-mini")


def cloud_configured() -> bool:
    return bool(COGNEE_CLOUD_URL and COGNEE_API_KEY)


def session_id_for(prospect_id: str) -> str:
    return f"prospect_{prospect_id}"
