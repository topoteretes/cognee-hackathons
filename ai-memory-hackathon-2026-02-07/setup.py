import cognee
import asyncio
from helper_functions import import_cognee_data
from cognee.api.v1.visualize.visualize import visualize_graph


async def main():
    # Clear ALL cognee data and system tables
    print("Clearing all cognee data...")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    print("✓ All data cleared\n")

    # Import everything (graph, vector, system DB, data storage)
    print("Importing data from export...")
    success = await import_cognee_data("cognee_export", verbose=True)
    
    if not success:
        print("\n✗ Import failed!")
        return
    
    # Create visualization
    print("\nCreating graph visualization...")
    await visualize_graph("./graphs/after_setup.html")
    
    print(f"\n{'='*60}")
    print(f"✓ Import verification complete!")
    print(f"  Graph visualization: ./graphs/after_setup.html")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())