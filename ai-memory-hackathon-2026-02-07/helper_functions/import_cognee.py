"""
Import Cognee Data
==================
This script imports previously exported Cognee data to fully restore a Cognee instance.

Imports:
- Graph database (Kuzu) - the knowledge graph structure
- Vector database (LanceDB) - embeddings for semantic search
- Data storage (raw files) - original text documents
- System database (SQLite) - user/principals tables and metadata

This allows complete restoration after running prune_system(metadata=True).

Usage:
    python import_cognee.py [export_directory]
    
Example:
    python import_cognee.py cognee_export
"""

import asyncio
import shutil
import json
import sys
from pathlib import Path
import cognee
import site


def find_cognee_paths():
    """Find cognee data directories in the site-packages"""
    # Look in all site-packages directories
    for site_dir in site.getsitepackages() + [site.getusersitepackages()]:
        site_path = Path(site_dir)
        cognee_path = site_path / "cognee"
        
        if cognee_path.exists():
            system_db = cognee_path / ".cognee_system"
            data_storage = cognee_path / ".data_storage"
            cache = cognee_path / ".cognee_cache"
            
            # Create directories if they don't exist
            system_db.mkdir(parents=True, exist_ok=True)
            (system_db / "databases").mkdir(parents=True, exist_ok=True)
            
            return {
                'system_databases': system_db / "databases",
                'data_storage': data_storage,
                'cache': cache if cache.exists() else None
            }
    
    return {}


async def import_cognee_data(import_dir="cognee_export", verbose=True):
    """
    Import Cognee data from an exported directory.
    
    Args:
        import_dir: Directory containing the exported Cognee data
        verbose: Whether to print progress messages (default: True)
    
    Returns:
        bool: True if import was successful, False otherwise
    """
    import_path = Path(import_dir)
    
    if not import_path.exists():
        if verbose:
            print(f"✗ Error: Import directory not found: {import_path.absolute()}")
            print("\nUsage: python import_cognee.py <export_directory>")
        return False
    
    # Check for metadata file
    metadata_file = import_path / "export_metadata.json"
    if metadata_file.exists() and verbose:
        with open(metadata_file) as f:
            metadata = json.load(f)
        print(f"Found export from: {metadata.get('export_date', 'unknown')}")
        print(f"Cognee version: {metadata.get('cognee_version', 'unknown')}")
    
    if verbose:
        print(f"\nStarting Cognee data import from: {import_path.absolute()}")
        print("=" * 60)
    
    # Find cognee paths
    paths = find_cognee_paths()
    
    if not paths:
        if verbose:
            print("✗ Error: Could not find cognee installation directories")
        return False
    
    # 1. Import ALL Databases (Graph, Vector, AND SQLite system database)
    if verbose:
        print("\n[1/2] Importing all databases...")
    try:
        source_db = import_path / "system_databases"
        
        if source_db.exists():
            target_db_path = paths.get('system_databases')
            
            # Remove existing databases directory completely
            if target_db_path and target_db_path.exists():
                shutil.rmtree(target_db_path)
                if verbose:
                    print(f"  - Removed existing databases")
            
            # Copy entire databases directory (includes all DBs)
            target_db_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_db, target_db_path)
            
            if verbose:
                print(f"  ✓ All databases imported to: {target_db_path}")
                # List what was imported
                graph_db = target_db_path / "cognee_graph_kuzu"
                vector_db = target_db_path / "cognee.lancedb"  # Actual name is cognee.lancedb
                sqlite_db = target_db_path / "cognee_db"  # SQLite is a file
                
                if graph_db.exists():
                    print(f"    - Graph database (Kuzu) ✓")
                if vector_db.exists():
                    print(f"    - Vector database (LanceDB) ✓")
                if sqlite_db.exists():
                    print(f"    - System database (SQLite) ✓")
        else:
            if verbose:
                print(f"  ! No databases found in export")
            return False
    except Exception as e:
        if verbose:
            print(f"  ✗ Error importing databases: {e}")
        return False
    
    # 2. Import Data Storage (raw files)
    if verbose:
        print("\n[2/2] Importing data storage...")
    try:
        source_storage = import_path / "data_storage"
        
        if source_storage.exists():
            target_storage_path = paths.get('data_storage')
            
            # Remove existing storage
            if target_storage_path and target_storage_path.exists():
                shutil.rmtree(target_storage_path)
                if verbose:
                    print(f"  - Removed existing storage at: {target_storage_path}")
            
            # Copy imported storage
            target_storage_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_storage, target_storage_path)
            if verbose:
                file_count = len(list(target_storage_path.rglob('*')))
                print(f"  ✓ Data storage imported to: {target_storage_path} ({file_count} files)")
        else:
            if verbose:
                print(f"  ! No data storage found in export")
    except Exception as e:
        if verbose:
            print(f"  ✗ Error importing data storage: {e}")
        return False
    
    if verbose:
        print("\n" + "=" * 60)
        print("✓ Import completed successfully!")
        print("\nYou can now use cognee.search() to query the imported data.")
        print("\nExample:")
        print("  import asyncio")
        print("  import cognee")
        print("  results = await cognee.search(query_text='your query', top_k=10)")
    
    return True


async def test_imported_data(verbose=True):
    """
    Test that the imported data is accessible via cognee.search()
    
    Args:
        verbose: Whether to print progress messages (default: True)
    
    Returns:
        bool: True if test was successful, False otherwise
    """
    if verbose:
        print("\n" + "=" * 60)
        print("Testing imported data with a sample search...")
        print("=" * 60)
    
    try:
        # Try a simple search
        results = await cognee.search(query_text="vendor", top_k=5)
        
        if verbose:
            if results:
                print(f"\n✓ Search successful! Found {len(results)} results.")
                print("\nSample results:")
                for i, result in enumerate(results[:3], 1):
                    print(f"  {i}. {result}")
            else:
                print("\n! Search returned no results (this may be normal if the dataset is empty)")
        
        return True
    except Exception as e:
        if verbose:
            print(f"\n✗ Error during search test: {e}")
        return False


if __name__ == "__main__":
    # Get import directory from command line argument or use default
    import_dir = sys.argv[1] if len(sys.argv) > 1 else "cognee_export"
    
    # Run the import
    success = asyncio.run(import_cognee_data(import_dir))
    
    # Optionally test the imported data
    if success:
        print("\n" + "=" * 60)
        user_input = input("Would you like to test the imported data with a sample search? (y/n): ")
        if user_input.lower() in ['y', 'yes']:
            asyncio.run(test_imported_data())

