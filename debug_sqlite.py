import sqlite3
from pathlib import Path

# Path to documents.db
db_path = Path("backend/data/documents.db").resolve()
print(f"Database path: {db_path}")

if not db_path.exists():
    print("❌ Database file not found!")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all documents
    cursor.execute("SELECT id, original_name, client_id, status FROM documents")
    rows = cursor.fetchall()
    
    print(f"\nFound {len(rows)} documents:")
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Name: {row[1]}")
        print(f"Client ID: {row[2]}")
        print(f"Status: {row[3]}")
        print("-" * 20)
        
    conn.close()

except Exception as e:
    print(f"❌ Error querying database: {e}")
