#!/usr/bin/env python3
"""
Database Cleanup Script - Removes orphaned document entries
"""

import sqlite3
from pathlib import Path

def clean_orphaned_entries():
    """Remove documents from database that don't have corresponding files"""
    print("🧹 CLEANING ORPHANED DATABASE ENTRIES")
    print("=" * 60)
    
    # Database and docs paths
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "data" / "documents.db"
    docs_dir = backend_dir / "data" / "docs"
    
    if not db_path.exists():
        print(f"❌ Database not found at: {db_path}")
        return
    
    print(f"📚 Database: {db_path}")
    print(f"📁 Docs directory: {docs_dir}")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all documents
    cursor.execute("SELECT id, filename, file_path, original_name FROM documents WHERE status != 'deleted'")
    documents = cursor.fetchall()
    
    print(f"\n📄 Found {len(documents)} documents in database\n")
    
    deleted_count = 0
    kept_count = 0
    
    for doc_id, filename, file_path, original_name in documents:
        # Check if file exists using both current path and expected path
        file_exists = False
        
        # Check current stored path
        if Path(file_path).exists():
            file_exists = True
        
        # Check expected path in docs directory
        expected_path = docs_dir / filename
        if expected_path.exists():
            file_exists = True
            # Update database with correct path if it was wrong
            if str(expected_path) != file_path:
                cursor.execute("UPDATE documents SET file_path = ? WHERE id = ?", (str(expected_path), doc_id))
                print(f"  ✅ Updated path for: {original_name}")
        
        if not file_exists:
            # File doesn't exist - mark as deleted
            cursor.execute("UPDATE documents SET status = 'deleted' WHERE id = ?", (doc_id,))
            deleted_count += 1
            print(f"  🗑️  Marked as deleted: {original_name}")
        else:
            kept_count += 1
            print(f"  ✅ Keeping: {original_name}")
    
    # Commit changes
    conn.commit()
    
    # Vacuum database to reclaim space
    print(f"\n🧹 Vacuuming database...")
    cursor.execute("VACUUM")
    
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"🎉 CLEANUP COMPLETED!")
    print(f"  ✅ Kept: {kept_count} documents")
    print(f"  🗑️  Removed: {deleted_count} orphaned entries")
    print(f"{'='*60}")
    
    if deleted_count > 0:
        print("\n🔄 Please restart the server to see the changes")
    else:
        print("\n✅ No orphaned entries found - database is clean!")

if __name__ == "__main__":
    clean_orphaned_entries()
