#!/usr/bin/env python3
"""Demo: Local cognee search with Ollama + Qdrant."""

import os
import sys
from pathlib import Path

os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv(override=True)

# Clear caches
from cognee.infrastructure.databases.vector.embeddings.config import get_embedding_config
from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import create_embedding_engine
from cognee.infrastructure.databases.vector.config import get_vectordb_config
from cognee.infrastructure.databases.vector.create_vector_engine import create_vector_engine

get_embedding_config.cache_clear()
create_embedding_engine.cache_clear()
get_vectordb_config.cache_clear()
create_vector_engine.cache_clear()

# Register Qdrant adapter
import cognee_community_vector_adapter_qdrant.register

import asyncio
import cognee
from cognee.api.v1.search import SearchType


async def main():
    print("=" * 50)
    print("Local Demo: cognee + Ollama + Qdrant")
    print("=" * 50)
    print()

    # Show config
    from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import get_embedding_engine
    engine = get_embedding_engine()
    print(f"Embeddings: {engine.model} ({engine.dimensions}-dim)")
    print(f"Endpoint:   {engine.endpoint}")
    print()

    # Interactive search
    while True:
        query = input("Search query (or 'quit'): ").strip()
        if query.lower() in ('quit', 'exit', 'q'):
            break
        if not query:
            continue

        print()
        results = await cognee.search(query, query_type=SearchType.CHUNKS)

        print(f"Found {len(results)} results:")
        for i, r in enumerate(results[:5], 1):
            text = str(r.get('text', r))[:100].replace('\n', ' ')
            print(f"  {i}. {text}...")
        print()


if __name__ == "__main__":
    asyncio.run(main())
