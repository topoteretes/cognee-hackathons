#!/usr/bin/env python3
"""Export Qdrant collection snapshots and upload to DigitalOcean Spaces."""

import os
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

HEADERS = {"api-key": QDRANT_API_KEY}
SNAPSHOT_DIR = Path("snapshots")
SNAPSHOT_DIR.mkdir(exist_ok=True)

# Collections to export
COLLECTIONS = [
    "DocumentChunk_text",
    "Entity_name",
    "TextDocument_name",
    "TextSummary_text",
    "EntityType_name",
    "EdgeType_relationship_name",
]


def create_snapshot(collection_name: str) -> str:
    """Create a snapshot for a collection and return the snapshot name."""
    print(f"Creating snapshot for {collection_name}...")

    resp = requests.post(
        f"{QDRANT_URL}/collections/{collection_name}/snapshots",
        headers=HEADERS
    )
    resp.raise_for_status()

    snapshot_name = resp.json()["result"]["name"]
    print(f"  Created: {snapshot_name}")
    return snapshot_name


def download_snapshot(collection_name: str, snapshot_name: str) -> Path:
    """Download a snapshot file."""
    print(f"Downloading {snapshot_name}...")

    resp = requests.get(
        f"{QDRANT_URL}/collections/{collection_name}/snapshots/{snapshot_name}",
        headers=HEADERS,
        stream=True
    )
    resp.raise_for_status()

    output_path = SNAPSHOT_DIR / f"{collection_name}.snapshot"
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Downloaded: {output_path} ({size_mb:.1f} MB)")
    return output_path


def main():
    print("=" * 60)
    print("Exporting Qdrant Snapshots")
    print("=" * 60)
    print()

    snapshot_files = []

    for collection in COLLECTIONS:
        try:
            snapshot_name = create_snapshot(collection)
            snapshot_path = download_snapshot(collection, snapshot_name)
            snapshot_files.append(snapshot_path)
        except Exception as e:
            print(f"  Error: {e}")

    print()
    print("=" * 60)
    print("Snapshots saved to ./snapshots/")
    print("=" * 60)

    # Create a combined archive
    import tarfile
    archive_path = Path("cognee-vectors-snapshot.tar.gz")
    print(f"\nCreating archive: {archive_path}")

    with tarfile.open(archive_path, "w:gz") as tar:
        for f in snapshot_files:
            tar.add(f, arcname=f.name)

    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(f"Archive created: {archive_path} ({size_mb:.1f} MB)")
    print()
    print("Upload this file to DigitalOcean Spaces:")
    print("  python upload_to_spaces.py cognee-vectors-snapshot.tar.gz")


if __name__ == "__main__":
    main()
