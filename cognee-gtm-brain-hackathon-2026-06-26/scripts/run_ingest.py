#!/usr/bin/env python3
"""Direct ingestion runner. Equivalent to `gtm-brain-ingest`."""

from gtm_brain.env import load_project_env
from gtm_brain.ingest import main


if __name__ == "__main__":
    load_project_env()
    main()
