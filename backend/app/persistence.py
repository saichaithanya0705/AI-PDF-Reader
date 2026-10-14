"""Select the document persistence backend at the application boundary."""

import os
from typing import Literal, cast

from .database import DocumentDatabase


PersistenceBackend = Literal["sqlite", "supabase"]


def persistence_backend() -> PersistenceBackend:
    configured = (os.getenv("PERSISTENCE_BACKEND") or "sqlite").strip().lower()
    if configured not in {"sqlite", "supabase"}:
        raise ValueError("PERSISTENCE_BACKEND must be either 'sqlite' or 'supabase'")
    return cast(PersistenceBackend, configured)


def create_document_database():
    if persistence_backend() == "supabase":
        from .supabase_database import SupabaseDatabase

        return SupabaseDatabase()
    return DocumentDatabase()


db = create_document_database()
