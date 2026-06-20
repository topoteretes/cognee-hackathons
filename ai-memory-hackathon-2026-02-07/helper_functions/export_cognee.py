"""
Export Cognee Data
==================
This script exports all Cognee data including:
- Graph database (Kuzu)
- Vector database (LanceDB)
- Data storage (raw files)
- System metadata

The exported data is saved to a 'cognee_export' directory that can be
transferred to another machine and imported using import_cognee.py
"""

import asyncio
import shutil
import json
from pathlib import Path
from datetime import datetime
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
            
            return {
                'system_databases': system_db / "databases" if system_db.exists() else None,
                'data_storage': data_storage if data_storage.exists() else None,
                'cache': cache if cache.exists() else None
            }
    
    return {}


async def export_cognee_data(export_dir="cognee_export"):
    """
    Export all Cognee data to a specified directory.
    
    Args:
        export_dir: Directory name where the export will be saved
    """
    export_path = Path(export_dir)
    export_path.mkdir(exist_ok=True)
    
    print(f"Starting Cognee data export to: {export_path.absolute()}")
    print("=" * 60)
    
    # Find cognee paths
    paths = find_cognee_paths()
    
    if not paths:
        print("✗ Error: Could not find cognee data directories")
        return
    
    # 1. Export System Databases (includes Kuzu graph, LanceDB vector, SQLite)
    print("\n[1/2] Exporting system databases...")
    try:
        system_db_path = paths.get('system_databases')
        
        if system_db_path and system_db_path.exists():
            target_db = export_path / "system_databases"
            shutil.copytree(system_db_path, target_db, dirs_exist_ok=True)
            print(f"  ✓ System databases exported: {system_db_path}")
            
            # Count what was exported
            graph_db = target_db / "cognee_graph_kuzu"
            vector_db = target_db / "cognee_vector_lancedb"
            if graph_db.exists():
                print(f"    - Graph database (Kuzu): {graph_db}")
            if vector_db.exists():
                print(f"    - Vector database (LanceDB): {vector_db}")
        else:
            print(f"  ! System databases not found")
    except Exception as e:
        print(f"  ✗ Error exporting system databases: {e}")
    
    # 2. Export Data Storage (raw files)
    print("\n[2/2] Exporting data storage...")
    try:
        data_storage_path = paths.get('data_storage')
        
        if data_storage_path and data_storage_path.exists():
            target_storage = export_path / "data_storage"
            shutil.copytree(data_storage_path, target_storage, dirs_exist_ok=True)
            file_count = len(list(target_storage.rglob('*')))
            print(f"  ✓ Data storage exported: {data_storage_path} ({file_count} files)")
        else:
            print(f"  ! Data storage not found")
    except Exception as e:
        print(f"  ✗ Error exporting data storage: {e}")
    
    # Save metadata about the export
    metadata = {
        "export_date": datetime.now().isoformat(),
        "cognee_version": cognee.__version__ if hasattr(cognee, '__version__') else "unknown",
        "export_components": [
            "graph_database",
            "vector_database", 
            "data_storage",
            "system_database"
        ]
    }
    
    with open(export_path / "export_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✓ Export completed successfully!")
    print(f"  Export location: {export_path.absolute()}")
    print(f"  Export size: {sum(f.stat().st_size for f in export_path.rglob('*') if f.is_file()) / 1024 / 1024:.2f} MB")
    print("\nTo import this data on another system, run:")
    print(f"  python import_cognee.py {export_dir}")


if __name__ == "__main__":
    asyncio.run(export_cognee_data())

