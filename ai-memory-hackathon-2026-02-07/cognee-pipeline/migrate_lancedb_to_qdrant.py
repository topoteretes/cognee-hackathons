"""
Migrate LanceDB data to Qdrant.

Reads the cognee 0.4.1 LanceDB export and uploads to Qdrant Cloud
with the correct schema for cognee 0.5.1 + Qdrant adapter.

Usage:
    cd cognee-pipeline
    uv run python migrate_lancedb_to_qdrant.py
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

import lancedb
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
)

# Paths
LANCEDB_PATH = "../cognee-minihack/cognee-minihack/cognee_export/system_databases/cognee.lancedb"

# Qdrant config
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Vector config (must match cognee's embedding model)
VECTOR_DIM = 768
VECTOR_NAME = "text"  # cognee 0.5.1 uses named vectors


def migrate():
    print("Connecting to LanceDB...")
    lance_db = lancedb.connect(LANCEDB_PATH)

    print("Connecting to Qdrant Cloud...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    # Get table names
    result = lance_db.list_tables()
    table_names = result.tables

    print(f"\nFound {len(table_names)} tables to migrate:")
    for name in table_names:
        table = lance_db.open_table(name)
        print(f"  - {name}: {table.count_rows()} rows")

    print("\n" + "=" * 60)

    for table_name in table_names:
        print(f"\nMigrating {table_name}...")

        # Read from LanceDB
        table = lance_db.open_table(table_name)
        df = table.to_pandas()
        row_count = len(df)

        if row_count == 0:
            print(f"  Skipping empty table")
            continue

        # Delete existing Qdrant collection if exists
        try:
            qdrant.delete_collection(table_name)
            print(f"  Deleted existing collection")
        except Exception:
            pass

        # Create new collection with named vectors
        qdrant.create_collection(
            collection_name=table_name,
            vectors_config={
                VECTOR_NAME: VectorParams(
                    size=VECTOR_DIM,
                    distance=Distance.COSINE,
                )
            },
        )
        print(f"  Created collection with named vector '{VECTOR_NAME}'")

        # Prepare points
        points = []
        for idx, row in df.iterrows():
            point_id = row["id"]
            vector = row["vector"].tolist() if hasattr(row["vector"], "tolist") else list(row["vector"])

            # Parse payload
            payload = row["payload"]
            if isinstance(payload, str):
                payload = json.loads(payload)

            points.append(
                PointStruct(
                    id=point_id,
                    vector={VECTOR_NAME: vector},
                    payload=payload,
                )
            )

        # Upload in batches
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            qdrant.upsert(collection_name=table_name, points=batch)
            print(f"  Uploaded {min(i + batch_size, len(points))}/{len(points)} points", end="\r")

        print(f"  Uploaded {len(points)} points                    ")

    print("\n" + "=" * 60)
    print("Migration complete!")

    # Verify
    print("\nVerifying collections:")
    for name in table_names:
        info = qdrant.get_collection(name)
        print(f"  - {name}: {info.points_count} points")


if __name__ == "__main__":
    migrate()
