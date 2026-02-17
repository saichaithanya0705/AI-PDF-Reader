
import sys
from pathlib import Path

# Add project root to path as run_app.py does
project_root = Path.cwd()
sys.path.insert(0, str(project_root))
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

try:
    import backend.app.supabase_database as sb_db
    print(f"Loaded 'backend.app.supabase_database' from: {sb_db.__file__}")
except ImportError as e:
    print(f"Failed to import backend.app.supabase_database: {e}")

try:
    from backend.app.supabase_database import SupabaseDatabase
    print(f"Imported SupabaseDatabase from: {sys.modules['backend.app.supabase_database'].__file__}")
except Exception as e:
    print(f"Failed to import SupabaseDatabase: {e}")
