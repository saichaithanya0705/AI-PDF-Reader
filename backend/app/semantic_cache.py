"""Semantic retrieval cache for RAG searches.

The cache is intentionally versioned by the user's SQLite library revision.
When PDFs are added, deleted, reingested, or metadata changes, the revision
changes and stale entries stop matching without needing fragile manual cleanup.
"""
from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class SemanticCacheContext:
    user_id: Optional[str]
    document_id: Optional[str]
    exclude_document_id: Optional[str]
    top_k: int
    use_advanced_rag: bool
    library_revision: str
    recency_intent: Optional[str] = None


@dataclass
class SemanticCacheEntry:
    normalized_query: str
    query_hash: str
    query_embedding: List[float]
    results: List[Any]
    created_at: float


class SemanticSearchCache:
    """Small LRU cache for exact and near-duplicate retrieval queries."""

    def __init__(self, max_entries: int = 256, similarity_threshold: float = 0.97):
        self.max_entries = max_entries
        self.similarity_threshold = similarity_threshold
        self._entries: OrderedDict[Tuple[Any, ...], List[SemanticCacheEntry]] = OrderedDict()
        self._global_revision = 0
        self._user_revisions: Dict[str, int] = {}

    def clear(self) -> None:
        self._entries.clear()

    def revision_for_user(self, user_id: Optional[str]) -> str:
        user_key = user_id or ""
        return f"rev-{self._global_revision}-{self._user_revisions.get(user_key, 0)}"

    def mark_library_changed(self, user_id: Optional[str] = None) -> str:
        if user_id is None:
            self._global_revision += 1
            self.clear()
            return self.revision_for_user(user_id)

        user_key = user_id or ""
        self._user_revisions[user_key] = self._user_revisions.get(user_key, 0) + 1
        self.invalidate_user(user_id)
        return self.revision_for_user(user_id)

    def normalize_query(self, query: str) -> str:
        return " ".join(re.findall(r"[a-z0-9]+", (query or "").lower()))

    def _query_hash(self, normalized_query: str) -> str:
        return hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()

    def _scope_key(self, context: SemanticCacheContext) -> Tuple[Any, ...]:
        return (
            context.user_id,
            context.document_id,
            context.exclude_document_id,
            int(context.top_k),
            bool(context.use_advanced_rag),
            context.library_revision,
            context.recency_intent,
        )

    def has_entries(self, context: SemanticCacheContext) -> bool:
        return bool(self._entries.get(self._scope_key(context)))

    def get_exact(self, query: str, context: SemanticCacheContext) -> Optional[List[Any]]:
        normalized_query = self.normalize_query(query)
        query_hash = self._query_hash(normalized_query)
        scope_key = self._scope_key(context)
        entries = self._entries.get(scope_key, [])

        for entry in entries:
            if entry.query_hash == query_hash:
                self._entries.move_to_end(scope_key)
                return self._clone_results(entry.results, hit_type="exact", similarity=1.0)

        return None

    def get_semantic(
        self,
        query_embedding: Iterable[float],
        context: SemanticCacheContext,
    ) -> Optional[List[Any]]:
        if context.recency_intent:
            return None

        scope_key = self._scope_key(context)
        entries = self._entries.get(scope_key, [])
        if not entries:
            return None

        query_vector = self._normalized_vector(query_embedding)
        best_entry = None
        best_similarity = 0.0

        for entry in entries:
            cached_vector = self._normalized_vector(entry.query_embedding)
            similarity = float(np.dot(query_vector, cached_vector))
            if similarity > best_similarity:
                best_similarity = similarity
                best_entry = entry

        if best_entry is None or best_similarity < self.similarity_threshold:
            return None

        self._entries.move_to_end(scope_key)
        return self._clone_results(best_entry.results, hit_type="semantic", similarity=best_similarity)

    def put(
        self,
        query: str,
        query_embedding: Iterable[float],
        context: SemanticCacheContext,
        results: List[Any],
    ) -> None:
        normalized_query = self.normalize_query(query)
        if not normalized_query:
            return

        scope_key = self._scope_key(context)
        entries = self._entries.setdefault(scope_key, [])
        query_hash = self._query_hash(normalized_query)

        entries[:] = [entry for entry in entries if entry.query_hash != query_hash]
        entries.append(
            SemanticCacheEntry(
                normalized_query=normalized_query,
                query_hash=query_hash,
                query_embedding=list(query_embedding),
                results=deepcopy(results),
                created_at=time.time(),
            )
        )
        self._entries.move_to_end(scope_key)
        self._prune()

    def invalidate_user(self, user_id: Optional[str]) -> None:
        if user_id is None:
            self.clear()
            return

        stale_keys = [key for key in self._entries if key[0] == user_id]
        for key in stale_keys:
            self._entries.pop(key, None)

    def invalidate_documents(self, document_ids: Iterable[str]) -> None:
        document_ids = {doc_id for doc_id in document_ids if doc_id}
        if not document_ids:
            return

        for key, entries in list(self._entries.items()):
            kept_entries = []
            for entry in entries:
                if any(getattr(result, "document_id", None) in document_ids for result in entry.results):
                    continue
                kept_entries.append(entry)

            if kept_entries:
                self._entries[key] = kept_entries
            else:
                self._entries.pop(key, None)

    def _clone_results(self, results: List[Any], hit_type: str, similarity: float) -> List[Any]:
        cloned_results = deepcopy(results)
        for result in cloned_results:
            metadata = getattr(result, "metadata", None) or {}
            metadata["retrieval_cache_hit"] = True
            metadata["retrieval_cache_hit_type"] = hit_type
            metadata["retrieval_cache_similarity"] = round(float(similarity), 4)
            result.metadata = metadata
        return cloned_results

    def _normalized_vector(self, embedding: Iterable[float]) -> np.ndarray:
        vector = np.asarray(list(embedding), dtype="float32")
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def _prune(self) -> None:
        while len(self._entries) > self.max_entries:
            self._entries.popitem(last=False)


_semantic_search_cache_instance: Optional[SemanticSearchCache] = None


def get_semantic_search_cache() -> SemanticSearchCache:
    global _semantic_search_cache_instance
    if _semantic_search_cache_instance is None:
        _semantic_search_cache_instance = SemanticSearchCache()
    return _semantic_search_cache_instance
