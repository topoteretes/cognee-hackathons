#!/usr/bin/env python3
"""Download and restore Qdrant snapshots from DigitalOcean Spaces."""

import os
import tarfile
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# DigitalOcean Spaces URL (update with your actual URL)
SPACES_URL = os.getenv(
    "SNAPSHOT_URL",
    "https://your-space.nyc3.digitaloceanspaces.com/cognee-vectors-snapshot.tar.gz"
)

# Local Qdrant URL (default for docker)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

SNAPSHOT_DIR = Path("snapshots")
ARCHIVE_PATH = Path("cognee-vectors-snapshot.tar.gz")


def download_archive():
    """Download the snapshot archive from DO Spaces."""
    if ARCHIVE_PATH.exists():
        print(f"Archive already exists: {ARCHIVE_PATH}")
        return

    print(f"Downloading from {SPACES_URL}...")
    resp = requests.get(SPACES_URL, stream=True)
    resp.raise_for_status()

    total_size = int(resp.headers.get('content-length', 0))
    downloaded = 0

    with open(ARCHIVE_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size:
                pct = (downloaded / total_size) * 100
                print(f"\r  {pct:.1f}% ({downloaded / 1024 / 1024:.1f} MB)", end="")

    print(f"\n  Downloaded: {ARCHIVE_PATH}")


def extract_archive():
    """Extract the snapshot archive."""
    print(f"Extracting {ARCHIVE_PATH}...")
    SNAPSHOT_DIR.mkdir(exist_ok=True)

    with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
        tar.extractall(SNAPSHOT_DIR)

    print(f"  Extracted to {SNAPSHOT_DIR}/")


def restore_snapshot(snapshot_file: Path):
    """Restore a snapshot to local Qdrant."""
    collection_name = snapshot_file.stem  # e.g., "DocumentChunk_text"

    print(f"Restoring {collection_name}...")

    headers = {}
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY

    # Upload snapshot file
    with open(snapshot_file, "rb") as f:
        resp = requests.post(
            f"{QDRANT_URL}/collections/{collection_name}/snapshots/upload",
            headers=headers,
            files={"snapshot": f},
            params={"priority": "snapshot"}  # Use snapshot data, not existing
        )

    if resp.status_code == 200:
        print(f"  Restored: {collection_name}")
    else:
        print(f"  Error: {resp.status_code} - {resp.text}")


def main():
    print("=" * 60)
    print("Restore Qdrant Snapshots from DigitalOcean Spaces")
    print("=" * 60)
    print()
    print(f"Source: {SPACES_URL}")
    print(f"Target: {QDRANT_URL}")
    print()

    # Step 1: Download
    download_archive()

    # Step 2: Extract
    extract_archive()

    # Step 3: Restore each collection
    print()
    print("Restoring collections...")
    for snapshot_file in SNAPSHOT_DIR.glob("*.snapshot"):
        restore_snapshot(snapshot_file)

    print()
    print("=" * 60)
    print("Done! Vectors restored to local Qdrant.")
    print("=" * 60)


if __name__ == "__main__":
    main()
