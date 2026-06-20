"""
Reindex raw procurement data into Qdrant via cognee.

This script reads all 2000 raw text files and processes them through
cognee's ECL pipeline to create properly formatted Qdrant collections.

Usage:
    cd cognee-pipeline
    cp .env.example .env  # configure Qdrant + LLM
    uv sync
    uv run python reindex.py

Options:
    --batch-size N    Process N documents at a time (default: 50)
    --skip-prune      Don't clear existing data before reindexing
    --dry-run         Count files without processing
"""

import os
import sys
import glob
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Register Qdrant adapter BEFORE importing cognee
import cognee_community_vector_adapter_qdrant.register

import cognee
from cognee.api.v1.search import SearchType


# Path to raw data files
RAW_DATA_DIR = Path(__file__).parent.parent / "cognee-minihack" / "cognee-minihack" / "cognee_export" / "data_storage"


async def setup():
    """Configure cognee to use Qdrant Cloud and your LLM provider."""
    # Configure LLM (OpenAI by default)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        print("cognee requires an LLM for entity extraction during cognify()")
        sys.exit(1)

    cognee.config.set_llm_api_key(api_key)
    cognee.config.set_llm_provider("openai")
    cognee.config.set_llm_model("gpt-4o-mini")

    # Configure vector DB
    cognee.config.set_vector_db_provider("qdrant")
    qdrant_url = os.getenv("QDRANT_URL") or os.getenv("VECTOR_DB_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")

    if not qdrant_url:
        print("ERROR: QDRANT_URL not set in .env")
        sys.exit(1)

    cognee.config.set_vector_db_url(qdrant_url)
    if qdrant_key:
        cognee.config.set_vector_db_key(qdrant_key)

    print("cognee configured:")
    print(f"  Vector DB: qdrant ({qdrant_url[:50]}...)")
    print(f"  LLM: openai / gpt-4o-mini")


def load_raw_files():
    """Load all raw text files from the data storage directory."""
    if not RAW_DATA_DIR.exists():
        print(f"ERROR: Raw data directory not found: {RAW_DATA_DIR}")
        sys.exit(1)

    files = sorted(RAW_DATA_DIR.glob("*.txt"))
    print(f"Found {len(files)} raw data files in {RAW_DATA_DIR}")
    return files


async def prune_existing_data():
    """Clear all existing cognee data for a fresh start."""
    print("\nPruning existing data...")
    try:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        print("Data pruned successfully.")
    except Exception as e:
        print(f"Warning: Prune failed (this is OK for first run): {e}")


async def reindex_data(files: list, batch_size: int = 50):
    """Process all files through cognee in batches."""
    total = len(files)
    print(f"\nReindexing {total} documents in batches of {batch_size}...")

    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch_files = files[batch_start:batch_end]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"\n--- Batch {batch_num}/{total_batches} (docs {batch_start + 1}-{batch_end}) ---")

        # Read and add documents in this batch
        for i, file_path in enumerate(batch_files):
            try:
                content = file_path.read_text()
                await cognee.add(content)
                if (i + 1) % 10 == 0:
                    print(f"  Added {i + 1}/{len(batch_files)} docs in batch")
            except Exception as e:
                print(f"  Error adding {file_path.name}: {e}")

        # Run cognify for this batch
        print(f"  Running cognify for batch {batch_num}...")
        try:
            await cognee.cognify()
            print(f"  Batch {batch_num} complete.")
        except Exception as e:
            print(f"  Error during cognify: {e}")
            # Continue with next batch even if this one fails


async def verify_reindex():
    """Run sample queries to verify the reindex worked."""
    print("\n--- Verification Queries ---\n")

    queries = [
        "Which vendors supply keyboards?",
        "Show transactions over $5000",
        "List all laptop purchases",
    ]

    for query in queries:
        print(f"Q: {query}")
        try:
            results = await cognee.search(
                query_text=query,
                query_type=SearchType.CHUNKS,
            )
            if results:
                for result in results[:2]:
                    text = str(result)[:150] + "..." if len(str(result)) > 150 else str(result)
                    print(f"  -> {text}")
            else:
                print("  -> No results")
        except Exception as e:
            print(f"  Error: {e}")
        print()


async def main():
    parser = argparse.ArgumentParser(description="Reindex raw procurement data into Qdrant via cognee")
    parser.add_argument("--batch-size", type=int, default=50, help="Documents per batch (default: 50)")
    parser.add_argument("--skip-prune", action="store_true", help="Don't clear existing data")
    parser.add_argument("--dry-run", action="store_true", help="Count files without processing")
    parser.add_argument("--sample", type=int, default=0, help="Process only N sample files (default: all)")
    args = parser.parse_args()

    # Load files
    files = load_raw_files()

    # Limit to sample if specified
    if args.sample > 0:
        files = files[:args.sample]
        print(f"Using sample of {len(files)} files")

    if args.dry_run:
        print(f"\nDry run: would process {len(files)} files in batches of {args.batch_size}")
        print(f"Total batches: {(len(files) + args.batch_size - 1) // args.batch_size}")
        return

    # Setup cognee
    await setup()

    # Prune if not skipped
    if not args.skip_prune:
        await prune_existing_data()

    # Reindex
    await reindex_data(files, batch_size=args.batch_size)

    # Verify
    await verify_reindex()

    print("\nReindex complete!")
    print("Your data is now in Qdrant Cloud as a knowledge graph.")
    print("Run the project apps to search, analyze, and detect anomalies.")


if __name__ == "__main__":
    asyncio.run(main())
