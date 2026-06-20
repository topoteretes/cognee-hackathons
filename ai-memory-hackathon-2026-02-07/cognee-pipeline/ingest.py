"""
cognee ingestion pipeline: process raw documents into a knowledge graph stored in Qdrant.

This is how the starter data was created. Run this to:
1. Add your own documents (text, CSV, PDF, etc.)
2. Run cognee.cognify() to extract entities, relationships, summaries
3. Store everything as vectors in your Qdrant Cloud cluster
4. Query with cognee.search() using graph-aware retrieval

Usage:
    cd cognee-pipeline
    cp .env.example .env  # configure Qdrant + LLM
    uv sync
    uv run python ingest.py
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

import cognee
from cognee.api.v1.search import SearchType


async def setup():
    """Configure cognee to use Qdrant Cloud and your LLM provider."""
    # Register Qdrant adapter
    from cognee_community_vector_adapter_qdrant import register

    # Configure LLM (OpenAI by default)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        cognee.config.set_llm_api_key(api_key)
        cognee.config.set_llm_provider("openai")
        cognee.config.set_llm_model("gpt-4o-mini")

    # Configure vector DB
    cognee.config.set_vector_db_provider("qdrant")
    qdrant_url = os.getenv("QDRANT_URL") or os.getenv("VECTOR_DB_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    if qdrant_url:
        cognee.config.set_vector_db_url(qdrant_url)
    if qdrant_key:
        cognee.config.set_vector_db_key(qdrant_key)

    print("cognee configured:")
    print(f"  Vector DB: qdrant")
    print(f"  LLM: openai / gpt-4o-mini")


async def ingest_sample_data():
    """Ingest sample procurement documents and build the knowledge graph."""
    # Sample procurement data (replace with your own files or text)
    documents = [
        """Invoice INV-2026-001 from TechSupply Co (Vendor V001):
        - 50x Dell Latitude 5550 Laptop ($1,200 each) = $60,000
        - 100x Logitech MX Master 3S Mouse ($99 each) = $9,900
        Total: $69,900 | Date: 2026-01-15 | Payment terms: Net 30""",

        """Invoice INV-2026-002 from OfficeMax Solutions (Vendor V002):
        - 200x Steelcase Series 1 Chair ($450 each) = $90,000
        - 50x Standing Desk Converter ($350 each) = $17,500
        Total: $107,500 | Date: 2026-01-18 | Discount: 5%""",

        """Transaction TXN-2026-0001: Wire transfer $69,900 to TechSupply Co
        Reference: INV-2026-001 | Date: 2026-02-14 | Status: Completed""",

        """Vendor Profile: TechSupply Co (V001)
        Category: IT Equipment | Rating: 4.8/5 | Active since: 2022
        Annual spend: $2.4M | Primary contact: procurement@techsupply.co""",
    ]

    print(f"\nIngesting {len(documents)} documents...")
    for i, doc in enumerate(documents):
        await cognee.add(doc)
        print(f"  Added document {i + 1}/{len(documents)}")

    print("\nRunning cognify (extracting entities, relationships, building knowledge graph)...")
    await cognee.cognify()
    print("Knowledge graph built.")


async def demo_search():
    """Demonstrate cognee's graph-aware search capabilities."""
    queries = [
        "Which vendors supply IT equipment?",
        "What was the total spend on office furniture?",
        "Show invoices related to TechSupply Co",
    ]

    print("\n--- Graph-Aware Search (cognee.search) ---\n")
    for query in queries:
        print(f"Q: {query}")
        try:
            results = await cognee.search(
                query_text=query,
                query_type=SearchType.CHUNKS,
            )
            for result in results[:3]:
                print(f"  -> {result}")
        except Exception as e:
            print(f"  Error: {e}")
        print()


async def main():
    await setup()

    # Clear previous data for a fresh start (required for first run)
    print("Pruning existing data...")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("Data pruned.")

    await ingest_sample_data()
    await demo_search()

    print("Done. Your data is now in Qdrant Cloud as a knowledge graph.")
    print("Run the project apps to search, analyze, and detect anomalies.")


if __name__ == "__main__":
    asyncio.run(main())
