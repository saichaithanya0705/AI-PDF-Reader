"""Durable PDF object storage with an ephemeral local processing cache."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from pathlib import PurePosixPath
from typing import Optional

from supabase import Client, create_client

from .persistence import persistence_backend
from .storage_paths import DOCS_DIR


class DocumentStorage:
    def store_pdf(
        self,
        *,
        user_id: str,
        document_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        raise NotImplementedError

    def ensure_local(self, location: str) -> Path:
        raise NotImplementedError

    def delete(self, location: str) -> None:
        raise NotImplementedError


class LocalDocumentStorage(DocumentStorage):
    def store_pdf(self, *, user_id: str, document_id: str, filename: str, content: bytes) -> str:
        path = (DOCS_DIR / filename).resolve()
        if DOCS_DIR.resolve() not in path.parents:
            raise ValueError("Invalid local PDF path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

    def ensure_local(self, location: str) -> Path:
        return Path(location).resolve()

    def delete(self, location: str) -> None:
        Path(location).unlink(missing_ok=True)


class SupabaseDocumentStorage(DocumentStorage):
    def __init__(
        self,
        url: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket: Optional[str] = None,
    ):
        self.url = (url or os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        self.secret_key = (
            secret_key
            or os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or ""
        ).strip()
        self.bucket = (bucket or os.getenv("SUPABASE_STORAGE_BUCKET") or "documents").strip()
        if not self.url or not self.secret_key:
            raise ValueError("Supabase document storage requires server-side project credentials")
        self.client: Client = create_client(self.url, self.secret_key)

    def _parse(self, location: str) -> tuple[str, str]:
        if not location.startswith("supabase://"):
            raise ValueError("Expected a Supabase object location")
        bucket, separator, key = location[len("supabase://"):].partition("/")
        if not separator or not bucket or not key:
            raise ValueError("Invalid Supabase object location")
        if bucket != self.bucket:
            raise ValueError("Supabase object location uses an unexpected bucket")
        self._validate_key(key)
        return bucket, key

    @staticmethod
    def _validate_uuid(value: str, label: str) -> str:
        try:
            return str(uuid.UUID(str(value)))
        except ValueError as exc:
            raise ValueError(f"{label} must be a UUID") from exc

    @classmethod
    def _validate_key(cls, key: str) -> tuple[str, str, str]:
        parts = PurePosixPath(key).parts
        if len(parts) != 3 or any(part in {"", ".", ".."} for part in parts):
            raise ValueError("Supabase document keys must be user/document/filename")
        user_id = cls._validate_uuid(parts[0], "user_id")
        document_id = cls._validate_uuid(parts[1], "document_id")
        filename = parts[2]
        if "/" in filename or "\\" in filename or not filename.lower().endswith(".pdf"):
            raise ValueError("Supabase document objects must be PDF files")
        return user_id, document_id, filename

    def _cache_path(self, key: str) -> Path:
        _, document_id, filename = self._validate_key(key)
        path = (DOCS_DIR / f"{document_id}_{filename}").resolve()
        if DOCS_DIR.resolve() not in path.parents:
            raise ValueError("Invalid Supabase cache path")
        return path

    @staticmethod
    def _write_cache(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + f".{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    def store_pdf(self, *, user_id: str, document_id: str, filename: str, content: bytes) -> str:
        normalized_user_id = self._validate_uuid(user_id, "user_id")
        normalized_document_id = self._validate_uuid(document_id, "document_id")
        if (
            "/" in filename
            or "\\" in filename
            or PurePosixPath(filename).name != filename
            or not filename.lower().endswith(".pdf")
        ):
            raise ValueError("filename must be a plain PDF filename")
        key = f"{normalized_user_id}/{normalized_document_id}/{filename}"
        self.client.storage.from_(self.bucket).upload(
            key,
            content,
            {"content-type": "application/pdf", "upsert": "false"},
        )
        cache_path = self._cache_path(key)
        self._write_cache(cache_path, content)
        return f"supabase://{self.bucket}/{key}"

    def ensure_local(self, location: str) -> Path:
        bucket, key = self._parse(location)
        cache_path = self._cache_path(key)
        if not cache_path.exists():
            content = self.client.storage.from_(bucket).download(key)
            self._write_cache(cache_path, content)
        return cache_path

    def delete(self, location: str) -> None:
        bucket, key = self._parse(location)
        self.client.storage.from_(bucket).remove([key])
        self._cache_path(key).unlink(missing_ok=True)


_storage: Optional[DocumentStorage] = None


def get_document_storage() -> DocumentStorage:
    global _storage
    if _storage is None:
        _storage = SupabaseDocumentStorage() if persistence_backend() == "supabase" else LocalDocumentStorage()
    return _storage
