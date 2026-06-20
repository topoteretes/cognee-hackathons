"""Project environment loader.

Loads the repo's top-level ``.env`` regardless of where Python is
invoked from, so ``uv run company-brain-ingest`` /
``uv run company-brain-slackbot`` / a direct ``python scripts/…`` call
all see the same configuration.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def project_env_path() -> Path:
    """Return the path to the repo's ``.env`` file."""
    return _PROJECT_ROOT / ".env"


def load_project_env(override: bool = False) -> None:
    """Load the project's ``.env`` into ``os.environ``.

    Safe to call multiple times. ``override=False`` matches python-dotenv
    defaults — existing environment variables win over file contents.
    """
    env_path = project_env_path()
    if env_path.exists():
        load_dotenv(env_path, override=override)
