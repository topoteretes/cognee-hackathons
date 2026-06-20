"""
Restore Qdrant snapshots to a Qdrant Cloud cluster.
Uploads each .snapshot file and restores it as a collection.

Usage:
    cp .env.example .env  # add your Qdrant Cloud URL and API key
    uv run python restore-snapshots.py
"""

import os
import glob
import requests
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.environ["QDRANT_URL"]
QDRANT_API_KEY = os.environ["QDRANT_API_KEY"]
SNAPSHOTS_DIR = os.path.join(os.path.dirname(__file__), "snapshots")

headers = {"api-key": QDRANT_API_KEY}


COLLECTION_NAMES = [
    "DocumentChunk_text",
    "EdgeType_relationship_name",
    "Entity_name",
    "EntityType_name",
    "TextDocument_name",
    "TextSummary_text",
]


def get_collection_name(filename: str) -> str:
    """Extract collection name from snapshot filename."""
    for name in COLLECTION_NAMES:
        if filename.startswith(name):
            return name
    return filename.removesuffix(".snapshot")


def restore_snapshot(filepath: str):
    collection = get_collection_name(os.path.basename(filepath))
    size_mb = os.path.getsize(filepath) / 1e6
    print(f"Restoring {collection} ({size_mb:.1f}MB)...")

    # Upload snapshot to the collection
    with open(filepath, "rb") as f:
        response = requests.post(
            f"{QDRANT_URL}/collections/{collection}/snapshots/upload",
            headers=headers,
            files={"snapshot": (os.path.basename(filepath), f)},
            params={"priority": "snapshot"},
            timeout=300,
        )

    if response.status_code == 200:
        print(f"  Restored {collection}")
    else:
        print(f"  Error restoring {collection}: {response.status_code} {response.text}")

    return response.status_code == 200


def main():
    snapshot_files = sorted(glob.glob(os.path.join(SNAPSHOTS_DIR, "*.snapshot")))
    if not snapshot_files:
        print(f"No snapshot files found in {SNAPSHOTS_DIR}/")
        print("Download the snapshots from the hackathon Google Drive first.")
        return

    print(f"Found {len(snapshot_files)} snapshots in {SNAPSHOTS_DIR}/")
    print(f"Restoring to {QDRANT_URL}\n")

    success = 0
    for filepath in snapshot_files:
        if restore_snapshot(filepath):
            success += 1

    print(f"\nDone: {success}/{len(snapshot_files)} collections restored.")

    # Verify
    print("\nVerifying collections:")
    for filepath in snapshot_files:
        collection = get_collection_name(os.path.basename(filepath))
        r = requests.get(f"{QDRANT_URL}/collections/{collection}", headers=headers)
        if r.status_code == 200:
            info = r.json()["result"]
            print(f"  {collection}: {info['points_count']} points")
        else:
            print(f"  {collection}: ERROR {r.status_code}")


if __name__ == "__main__":
    main()
