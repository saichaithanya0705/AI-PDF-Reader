#!/usr/bin/env python3
"""
Startup script for Adobe PDF Intelligence Application
Handles Python path setup and starts the server
"""

import sys
import os
from pathlib import Path

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Also add backend directory to path
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Set environment variables
os.environ["PYTHONPATH"] = f"{project_root}{os.pathsep}{backend_path}"

# Now import and run uvicorn
try:
    import uvicorn
    print("🚀 Starting Adobe PDF Intelligence Application...")
    print(f"📁 Project root: {project_root}")
    print(f"🐍 Python path: {sys.path[:3]}...")
    # Use PORT env variable (for production) or default to 8080
    port = int(os.environ.get("PORT", 8080))
    print(f"🌐 Server will be available at: http://localhost:{port}")
    print("=" * 60)

    # Start the server
    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
except ImportError as e:
    print(f"❌ Error importing uvicorn: {e}")
    print("💡 Please install uvicorn: pip install uvicorn")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting server: {e}")
    sys.exit(1)
