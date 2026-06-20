"""CLI entrypoints exposed via [project.scripts]."""

from __future__ import annotations

from .env import load_project_env
from .ingest import main as ingest_main


def main() -> None:
    load_project_env()
    ingest_main()


if __name__ == "__main__":
    main()
