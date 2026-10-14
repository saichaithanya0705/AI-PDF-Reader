"""Canonical runtime storage paths for local and hosted deployments."""

import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """Resolve the configured data root relative to the backend directory."""
    configured = (os.getenv("APP_DATA_DIR") or "").strip()
    if not configured:
        return (BACKEND_DIR / "data").resolve()

    candidate = Path(configured).expanduser()
    if not candidate.is_absolute():
        candidate = BACKEND_DIR / candidate
    return candidate.resolve()


DATA_DIR = get_data_dir()
DOCS_DIR = DATA_DIR / "docs"
