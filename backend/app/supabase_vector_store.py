"""Vector-search adapter backed by Supabase pgvector RPCs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .supabase_database import SupabaseDatabase
from .vector_store import SearchResult


class SupabaseVectorStore:
    def __init__(self, database: SupabaseDatabase):
        self.database = database

    def add_documents(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        if len(embeddings) != len(metadatas):
            raise ValueError("Embeddings and metadata must have the same length")
        chunk_ids = [metadata.get("chunk_id") for metadata in metadatas]
        if any(not chunk_id for chunk_id in chunk_ids):
            raise ValueError("Every persisted vector requires a document chunk ID")
        return chunk_ids

    add_embeddings = add_documents

    def remove_document(self, document_id: str) -> int:
        # Chunk deletion is owned transactionally by SupabaseDatabase.
        return 0

    def search_similar(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        exclude_document_id: Optional[str] = None,
    ) -> List[SearchResult]:
        tenant_id = self.database._require_user_id(user_id)
        params = {
            "query_embedding": query_embedding,
            "filter_user_id": tenant_id,
            "match_count": max(1, min(int(top_k or 1), 50)),
            "match_threshold": 0.0,
            "filter_document_id": document_id,
        }
        if exclude_document_id:
            # The exclusion must happen before LIMIT. When the query is built from
            # the open page, that document's own chunks are always the nearest
            # neighbours, so filtering after LIMIT leaves nothing for other PDFs.
            try:
                response = self.database.client.rpc(
                    "match_document_chunks",
                    {**params, "exclude_document_id": exclude_document_id},
                ).execute()
            except Exception as exc:
                # Database predates the exclude_document_id migration: over-fetch
                # and filter client-side instead.
                print(f"⚠️ match_document_chunks lacks exclude_document_id ({exc}); over-fetching")
                response = self.database.client.rpc(
                    "match_document_chunks", {**params, "match_count": 50}
                ).execute()
        else:
            response = self.database.client.rpc("match_document_chunks", params).execute()
        results: List[SearchResult] = []
        for row in response.data or []:
            if exclude_document_id and str(row["document_id"]) == str(exclude_document_id):
                continue
            metadata = dict(row.get("metadata") or {})
            results.append(
                SearchResult(
                    chunk_id=str(row["id"]),
                    document_id=str(row["document_id"]),
                    chunk_text=row["chunk_text"],
                    chunk_index=int(row["chunk_index"]),
                    page_number=int(row["page_number"]),
                    similarity_score=float(row["similarity"]),
                    user_id=tenant_id,
                    metadata=metadata,
                )
            )
            if len(results) >= top_k:
                break
        return results

    def get_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        tenant_id = self.database._require_user_id(user_id)
        count = self.database.get_chunk_count(client_id=tenant_id)
        return {
            "total_vectors": count,
            "num_documents": None,
            "index_type": "Supabase pgvector HNSW",
        }
