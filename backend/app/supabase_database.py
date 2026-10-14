"""Supabase-backed document and RAG persistence with tenant-scoped queries."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from .database import Document


logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _storage_location(file_path: str) -> tuple[str, str]:
    prefix = "supabase://"
    if not file_path.startswith(prefix):
        raise ValueError("Supabase documents must use a supabase://bucket/object-key path")
    bucket, separator, object_key = file_path[len(prefix):].partition("/")
    if not separator or not bucket or not object_key:
        raise ValueError("Invalid Supabase document storage path")
    return bucket, object_key


class SupabaseDatabase:
    """Implements the live DocumentDatabase contract using Supabase Postgres."""

    def __init__(self, url: Optional[str] = None, secret_key: Optional[str] = None):
        self.url = (url or os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
        self.secret_key = (
            secret_key
            or os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or ""
        ).strip()
        if not self.url or not self.secret_key:
            raise ValueError(
                "Supabase persistence requires SUPABASE_URL and SUPABASE_SECRET_KEY "
                "(or the legacy SUPABASE_SERVICE_KEY)"
            )
        self.client: Client = create_client(self.url, self.secret_key)

    @staticmethod
    def _require_user_id(client_id: Optional[str]) -> str:
        if not client_id:
            raise ValueError("A tenant user ID is required for this persistence operation")
        try:
            return str(uuid.UUID(str(client_id)))
        except ValueError as exc:
            raise ValueError("Supabase persistence requires an authenticated UUID user ID") from exc

    @staticmethod
    def _row_to_document(row: Dict[str, Any]) -> Document:
        bucket = row.get("storage_bucket") or "documents"
        key = row.get("storage_key") or ""
        return Document(
            id=str(row["id"]),
            filename=row["filename"],
            original_name=row["original_name"],
            upload_date=_parse_timestamp(row.get("upload_date")) or _utc_now(),
            file_size=int(row["file_size"]),
            file_path=f"supabase://{bucket}/{key}",
            status=row.get("status") or "uploaded",
            client_id=str(row["user_id"]),
            persona=row.get("persona"),
            job_role=row.get("job_role"),
            processing_status=row.get("processing_status") or "pending",
            validation_result=row.get("validation_result"),
            metadata=row.get("metadata") or {},
            last_uploaded=_parse_timestamp(row.get("last_uploaded")),
            last_opened=_parse_timestamp(row.get("last_opened")),
            last_accessed=_parse_timestamp(row.get("last_accessed")),
            tags=row.get("tags") or [],
            file_hash=row.get("file_hash"),
        )

    def _notify_library_changed(self, client_id: Optional[str]) -> None:
        try:
            from .semantic_cache import get_semantic_search_cache

            get_semantic_search_cache().mark_library_changed(client_id)
        except Exception as exc:
            logger.warning("Could not invalidate semantic cache for %s: %s", client_id, exc)

    def create_document(
        self,
        filename: str,
        original_name: str,
        file_size: int,
        file_path: str,
        client_id: Optional[str] = None,
        persona: Optional[str] = None,
        job_role: Optional[str] = None,
        validation_result: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        file_hash: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> Document:
        user_id = self._require_user_id(client_id)
        bucket, storage_key = _storage_location(file_path)
        now = _utc_now().isoformat()
        payload = {
            "id": document_id or str(uuid.uuid4()),
            "user_id": user_id,
            "storage_bucket": bucket,
            "storage_key": storage_key,
            "filename": filename,
            "original_name": original_name,
            "mime_type": "application/pdf",
            "file_size": int(file_size),
            "file_hash": file_hash,
            "persona": persona,
            "job_role": job_role,
            "validation_result": validation_result,
            "metadata": metadata or {},
            "last_uploaded": now,
            "status": "uploaded",
            "processing_status": "pending",
        }
        result = self.client.table("documents").insert(payload).execute()
        if not result.data:
            raise RuntimeError("Supabase did not return the created document")
        self._notify_library_changed(user_id)
        return self._row_to_document(result.data[0])

    def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        client_id: Optional[str] = None,
    ) -> List[Document]:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("documents")
            .select("*")
            .eq("user_id", user_id)
            .neq("status", "deleted")
        )
        query = query.order("last_opened", desc=True, nullsfirst=False).order("upload_date", desc=True)
        if limit:
            query = query.range(offset, offset + int(limit) - 1)
        elif offset:
            query = query.range(offset, offset + 999)
        result = query.execute()
        return [self._row_to_document(row) for row in result.data or []]

    def get_document_by_id(self, document_id: str, client_id: Optional[str] = None) -> Optional[Document]:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("documents")
            .select("*")
            .eq("id", document_id)
            .eq("user_id", user_id)
            .neq("status", "deleted")
        )
        result = query.limit(1).execute()
        return self._row_to_document(result.data[0]) if result.data else None

    def get_document_by_filename(self, filename: str, client_id: Optional[str] = None) -> Optional[Document]:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("documents")
            .select("*")
            .eq("filename", filename)
            .eq("user_id", user_id)
            .neq("status", "deleted")
        )
        result = query.limit(1).execute()
        return self._row_to_document(result.data[0]) if result.data else None

    def update_document(self, document_id: str, client_id: Optional[str] = None, **updates: Any) -> bool:
        if not updates:
            return False
        allowed = {
            "status", "processing_status", "persona", "job_role", "validation_result",
            "metadata", "last_uploaded", "last_opened", "last_accessed", "tags",
        }
        unknown = set(updates) - allowed - {"updated_at"}
        if unknown:
            raise ValueError(f"Unsupported document update fields: {sorted(unknown)}")
        payload = {key: _iso(value) for key, value in updates.items() if key != "updated_at"}
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("documents")
            .update(payload)
            .eq("id", document_id)
            .eq("user_id", user_id)
        )
        result = query.execute()
        changed = bool(result.data)
        if changed:
            self._notify_library_changed(user_id)
        return changed

    def delete_document(
        self,
        document_id: str,
        soft_delete: bool = True,
        client_id: Optional[str] = None,
    ) -> bool:
        user_id = self._require_user_id(client_id)
        if soft_delete:
            return self.update_document(document_id, client_id=user_id, status="deleted")
        query = (
            self.client.table("documents")
            .delete()
            .eq("id", document_id)
            .eq("user_id", user_id)
        )
        result = query.execute()
        changed = bool(result.data)
        if changed:
            self._notify_library_changed(user_id)
        return changed

    def update_last_opened(self, document_id: str, client_id: Optional[str] = None) -> bool:
        return self.update_document(document_id, client_id=client_id, last_opened=_utc_now())

    def update_last_uploaded(self, document_id: str, client_id: Optional[str] = None) -> bool:
        return self.update_document(document_id, client_id=client_id, last_uploaded=_utc_now())

    def get_documents_by_client(
        self, client_id: str, limit: Optional[int] = None, offset: int = 0
    ) -> List[Document]:
        return self.get_all_documents(limit=limit, offset=offset, client_id=client_id)

    def search_documents(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        client_id: Optional[str] = None,
    ) -> List[Document]:
        fields = fields or ["original_name", "filename", "persona", "job_role"]
        needle = (query or "").casefold()
        return [
            document
            for document in self.get_all_documents(client_id=client_id)
            if any(needle in str(getattr(document, field, "") or "").casefold() for field in fields)
        ]

    def get_document_stats(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        documents = self.get_all_documents(client_id=client_id)
        return {
            "total_documents": len(documents),
            "uploaded_documents": sum(document.status == "uploaded" for document in documents),
            "processed_documents": sum(document.processing_status == "completed" for document in documents),
            "opened_documents": sum(document.last_opened is not None for document in documents),
            "total_size_bytes": sum(document.file_size for document in documents),
        }

    def find_duplicate_by_hash(self, file_hash: str, client_id: Optional[str] = None) -> Optional[Document]:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("documents")
            .select("*")
            .eq("file_hash", file_hash)
            .eq("user_id", user_id)
            .neq("status", "deleted")
        )
        result = query.limit(1).execute()
        return self._row_to_document(result.data[0]) if result.data else None

    def store_chunk(
        self,
        document_id: str,
        chunk_text: str,
        chunk_index: int,
        page_number: int,
        embedding: Optional[List[float]] = None,
        char_count: Optional[int] = None,
        word_count: Optional[int] = None,
        client_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        user_id = self._require_user_id(client_id)
        if embedding is None:
            raise ValueError("Supabase vector persistence requires an embedding")
        payload = {
            "id": chunk_id or str(uuid.uuid4()),
            "document_id": document_id,
            "user_id": user_id,
            "chunk_text": chunk_text,
            "chunk_index": int(chunk_index),
            "page_number": int(page_number),
            "embedding": embedding,
            "char_count": char_count,
            "word_count": word_count,
            "metadata": metadata or {},
        }
        result = self.client.table("document_chunks").insert(payload).execute()
        if not result.data:
            raise RuntimeError("Supabase did not return the created document chunk")
        self._notify_library_changed(user_id)
        return str(result.data[0]["id"])

    def get_chunks_by_document(self, document_id: str, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("document_chunks")
            .select("id,document_id,chunk_text,chunk_index,page_number,char_count,word_count,metadata,created_at")
            .eq("document_id", document_id)
            .eq("user_id", user_id)
        )
        result = query.order("chunk_index").execute()
        return list(result.data or [])

    def get_document_metadata(
        self, document_id: str, client_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        chunks = self.get_chunks_by_document(document_id, client_id=client_id)[:10]
        return [
            {
                "page": chunk["page_number"],
                "text": chunk["chunk_text"],
                "embedding_vector": None,
            }
            for chunk in chunks
        ]

    def delete_chunks_by_document(self, document_id: str, client_id: Optional[str] = None) -> int:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("document_chunks")
            .delete()
            .eq("document_id", document_id)
            .eq("user_id", user_id)
        )
        result = query.execute()
        deleted = len(result.data or [])
        if deleted:
            self._notify_library_changed(user_id)
        return deleted

    def search_chunks_bm25(
        self,
        query: str,
        limit: int = 20,
        document_id: Optional[str] = None,
        exclude_document_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        user_id = self._require_user_id(client_id)
        params = {
            "search_query": query,
            "filter_user_id": user_id,
            "match_count": max(1, min(int(limit or 1), 100)),
            "filter_document_id": document_id,
            "exclude_document_id": exclude_document_id,
        }
        result = self.client.rpc("search_document_chunks_fts", params).execute()
        rows = list(result.data or [])
        max_rank = max((float(row.get("bm25_score") or 0.0) for row in rows), default=0.0)
        for row in rows:
            score = float(row.get("bm25_score") or 0.0)
            metadata = dict(row.get("metadata") or {})
            metadata.update({
                "document_name": row.get("original_name") or row.get("filename") or "Unknown Document",
                "filename": row.get("filename"),
                "original_name": row.get("original_name"),
                "file_path": row.get("file_path"),
                "upload_date": row.get("upload_date"),
                "last_uploaded": row.get("last_uploaded") or row.get("upload_date"),
                "last_opened": row.get("last_opened"),
                "last_accessed": row.get("last_accessed"),
                "retrieval_source": "bm25",
                "bm25_score": score,
                "keyword_score": score / max_rank if max_rank > 0 else 0.0,
            })
            row["metadata"] = metadata
        return rows

    def get_library_revision(self, client_id: Optional[str] = None) -> str:
        user_id = self._require_user_id(client_id)
        documents = self.client.table("documents").select(
            "id,status,processing_status,updated_at"
        ).eq("user_id", user_id).order("id").execute().data or []
        chunks = self.client.table("document_chunks").select(
            "id,document_id,created_at"
        ).eq("user_id", user_id).order("id").execute().data or []
        payload = json.dumps(
            {"user_id": user_id, "documents": documents, "chunks": chunks},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_chunk_count(self, document_id: Optional[str] = None, client_id: Optional[str] = None) -> int:
        user_id = self._require_user_id(client_id)
        query = (
            self.client.table("document_chunks")
            .select("id", count="exact")
            .eq("user_id", user_id)
        )
        if document_id:
            query = query.eq("document_id", document_id)
        result = query.limit(1).execute()
        return int(result.count or 0)
