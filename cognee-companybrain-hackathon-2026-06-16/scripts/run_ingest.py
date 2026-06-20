#!/usr/bin/env python3
"""Direct ingestion runner. Equivalent to `company-brain-ingest`."""

from company_brain.env import load_project_env
from company_brain.ingest import main


if __name__ == "__main__":
    load_project_env()
    main()
