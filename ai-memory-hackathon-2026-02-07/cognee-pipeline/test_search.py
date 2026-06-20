#!/usr/bin/env python3
"""Test cognee.search() with correct configuration."""

import os
from pathlib import Path

# Change to project directory and load .env
os.chdir(Path(__file__).parent)

from dotenv import load_dotenv
load_dotenv(override=True)

# Clear cached configs BEFORE importing cognee
from cognee.infrastructure.databases.vector.embeddings.config import get_embedding_config
from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import create_embedding_engine
from cognee.infrastructure.databases.vector.config import get_vectordb_config
from cognee.infrastructure.databases.vector.create_vector_engine import create_vector_engine

get_embedding_config.cache_clear()
create_embedding_engine.cache_clear()
get_vectordb_config.cache_clear()
create_vector_engine.cache_clear()

# Register Qdrant adapter (import triggers registration)
import cognee_community_vector_adapter_qdrant.register

import asyncio
import cognee
from cognee.api.v1.search import SearchType

async def main():
    print("=" * 60)
    print("cognee.search() Test with Ollama + nomic-embed-text")
    print("=" * 60)
    print()

    # Verify engine config
    from cognee.infrastructure.databases.vector.embeddings.get_embedding_engine import get_embedding_engine
    engine = get_embedding_engine()
    print(f"Embedding: {type(engine).__name__} ({engine.model})")
    print(f"Dimensions: {engine.dimensions}")
    print()

    # Test queries
    queries = [
        "What is procurement?",
        "Tell me about vendor payments",
        "Show me transactions for office supplies",
    ]

    for query in queries:
        print(f"Query: '{query}'")
        print("-" * 40)

        results = await cognee.search(query, query_type=SearchType.CHUNKS)

        print(f"Results: {len(results)}")
        for i, result in enumerate(results[:3]):
            text = result.get('text', str(result))
            if isinstance(text, dict):
                # Handle nested dict
                text = str(text)
            text = text[:150].replace('\n', ' ')
            print(f"  {i+1}. {text}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())
