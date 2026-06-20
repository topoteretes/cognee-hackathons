#!/usr/bin/env python3
"""Download and restore Qdrant snapshots for local setup."""

import os
import sys
import tarfile
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SNAPSHOT_URL = os.getenv(
    "SNAPSHOT_URL",
    "https://cognee-data.nyc3.digitaloceanspaces.com/cognee-vectors-snapshot.tar.gz"  # 91MB
)
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

SNAPSHOT_DIR = Path("snapshots")
ARCHIVE_PATH = Path("cognee-vectors-snapshot.tar.gz")


def check_qdrant():
    """Verify Qdrant is running."""
    try:
        resp = requests.get(f"{QDRANT_URL}/collections", timeout=5)
        resp.raise_for_status()
        print(f"[OK] Qdrant running at {QDRANT_URL}")
        return True
    except Exception as e:
        print(f"[ERROR] Qdrant not reachable at {QDRANT_URL}")
        print(f"        Run: docker compose up -d")
        return False


def download_archive():
    """Download snapshot archive from DO Spaces."""
    if ARCHIVE_PATH.exists():
        size_mb = ARCHIVE_PATH.stat().st_size / (1024 * 1024)
        print(f"[OK] Archive exists: {ARCHIVE_PATH} ({size_mb:.1f} MB)")
        return True

    print(f"Downloading from {SNAPSHOT_URL}...")
    try:
        resp = requests.get(SNAPSHOT_URL, stream=True, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        return False

    total = int(resp.headers.get('content-length', 0))
    downloaded = 0

    with open(ARCHIVE_PATH, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = (downloaded / total) * 100
                print(f"\r  {pct:.1f}% ({downloaded // 1024 // 1024} MB)", end="", flush=True)

    print(f"\n[OK] Downloaded: {ARCHIVE_PATH}")
    return True


def extract_archive():
    """Extract snapshot files."""
    print(f"Extracting {ARCHIVE_PATH}...")
    SNAPSHOT_DIR.mkdir(exist_ok=True)

    with tarfile.open(ARCHIVE_PATH, "r:gz") as tar:
        tar.extractall(SNAPSHOT_DIR)

    files = list(SNAPSHOT_DIR.glob("*.snapshot"))
    print(f"[OK] Extracted {len(files)} snapshots")
    return files


def restore_snapshot(snapshot_file: Path):
    """Restore a single snapshot to Qdrant."""
    collection = snapshot_file.stem

    with open(snapshot_file, "rb") as f:
        resp = requests.post(
            f"{QDRANT_URL}/collections/{collection}/snapshots/upload",
            files={"snapshot": f},
            params={"priority": "snapshot"},
            timeout=120
        )

    if resp.status_code == 200:
        print(f"  [OK] {collection}")
        return True
    else:
        print(f"  [ERROR] {collection}: {resp.status_code}")
        return False


def main():
    print("=" * 50)
    print("Local Setup: Restore Qdrant Vectors")
    print("=" * 50)
    print()

    # Check Qdrant
    if not check_qdrant():
        sys.exit(1)

    # Download
    if not download_archive():
        sys.exit(1)

    # Extract
    snapshots = extract_archive()

    # Restore
    print()
    print("Restoring collections...")
    success = 0
    for snap in snapshots:
        if restore_snapshot(snap):
            success += 1

    print()
    print("=" * 50)
    print(f"Restored {success}/{len(snapshots)} collections")
    print("Run: python demo.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
