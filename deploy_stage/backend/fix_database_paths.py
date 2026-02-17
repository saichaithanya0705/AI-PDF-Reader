#!/usr/bin/env python3
"""
Quick Database Path Fix Script
Fixes incorrect file paths in the database
"""

import sqlite3
from pathlib import Path
import os

def fix_database_paths():
    """Fix incorrect file paths in the database"""
    print("🔧 FIXING DATABASE FILE PATHS")
    print("=" * 50)
    
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
    
    # Get all documents with their current file paths
    cursor.execute("SELECT id, filename, file_path, original_name FROM documents WHERE status != 'deleted'")
    documents = cursor.fetchall()
    
    print(f"📄 Found {len(documents)} documents to check")
    
    fixed_count = 0
    for doc_id, filename, current_path, original_name in documents:
        # Check if current path is incorrect
        needs_fix = False
        
        if "D:\\" in current_path:
            needs_fix = True
            print(f"  🔍 Found D:\\ path: {original_name}")
        elif "backend\\data\\backend" in current_path:
            needs_fix = True
            print(f"  🔍 Found nested backend path: {original_name}")
        elif not Path(current_path).exists():
            needs_fix = True
            print(f"  🔍 File not found at current path: {original_name}")
        
        if needs_fix:
            # Create correct path
            correct_path = docs_dir / filename
            if correct_path.exists():
                cursor.execute("UPDATE documents SET file_path = ? WHERE id = ?", (str(correct_path), doc_id))
                fixed_count += 1
                print(f"    ✅ Fixed: {original_name}")
            else:
                print(f"    ❌ File not found at correct location: {correct_path}")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n🎉 COMPLETED!")
    print(f"✅ Fixed {fixed_count} file paths")
    print(f"📊 Total documents: {len(documents)}")
    
    if fixed_count > 0:
        print("\n🔄 Please restart the server to see the changes")
    else:
        print("\n✅ All file paths are already correct")

if __name__ == "__main__":
    fix_database_paths()
