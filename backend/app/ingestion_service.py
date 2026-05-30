"""Canonical document ingestion service for SQLite records and FAISS vectors."""
from __future__ import annotations

import time
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .chunking_service import DocumentChunk, chunking_service
from .database import Document, db
from .embedding_service import get_embedding_service
from .vector_store import get_vector_store


logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Owns the full RAG ingestion lifecycle for uploaded PDFs."""

    def __init__(self):
        self.chunking_service = chunking_service
        self.embedding_service = get_embedding_service()
        self.vector_store = get_vector_store()

    async def process_document(
        self,
        document_id: str,
        user_id: str,
        mode: str = "single",
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """Process one document through SQLite chunk storage and FAISS indexing."""
        start_time = time.time()
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            return {"success": False, "document_id": document_id, "error": "Document not found"}

        ingestion_cleared = False
        try:
            self._validate_document_file(document)
            db.update_document(
                document.id,
                client_id=user_id,
                processing_status="processing",
                status="uploaded",
            )

            ingestion_cleared = True
            self._clear_existing_ingestion(document.id)

            chunks = self.chunking_service.chunk_document(
                pdf_path=document.file_path,
                document_id=document.id,
                document_name=self._document_name(document),
                mode=mode,
                persona=document.persona,
                job=document.job_role,
            )
            if not chunks:
                raise ValueError("No text chunks could be created from the document")

            result = self._persist_chunks(
                document=document,
                user_id=user_id,
                chunks=chunks,
                batch_size=batch_size,
            )

            elapsed = round(time.time() - start_time, 2)
            metadata = self._merge_metadata(
                document.metadata,
                {
                    "ingestion": {
                        "mode": mode,
                        "source": "canonical_ingestion_service",
                        "chunks_created": result["chunks_stored"],
                        "vectors_added": result["vectors_added"],
                        "elapsed_seconds": elapsed,
                    }
                },
            )
            db.update_document(
                document.id,
                client_id=user_id,
                processing_status="completed",
                status="processed",
                metadata=metadata,
            )

            return {
                "success": True,
                "document_id": document.id,
                "mode": mode,
                "chunks_created": result["chunks_stored"],
                "embeddings_generated": result["embeddings_generated"],
                "chunks_stored": result["chunks_stored"],
                "vectors_added": result["vectors_added"],
                "elapsed_seconds": elapsed,
            }

        except Exception as exc:
            if ingestion_cleared:
                self._cleanup_failed_ingestion(document.id)
            db.update_document(
                document.id,
                client_id=user_id,
                processing_status="failed",
                metadata=self._merge_metadata(
                    document.metadata,
                    {"ingestion": {"mode": mode, "error": str(exc)}},
                ),
            )
            return {"success": False, "document_id": document.id, "error": str(exc)}

    async def process_collection(
        self,
        document_ids: Iterable[str],
        user_id: str,
        persona: Optional[str] = None,
        job: Optional[str] = None,
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """Process multiple PDFs through the multi-document chunking algorithm."""
        start_time = time.time()
        documents: List[Document] = []
        missing: List[str] = []

        for document_id in document_ids:
            document = db.get_document_by_id(document_id, client_id=user_id)
            if not document:
                missing.append(document_id)
                continue
            documents.append(document)

        if missing:
            return {"success": False, "error": "Documents not found", "missing_document_ids": missing}
        if not documents:
            return {"success": False, "error": "No documents supplied"}

        cleared_document_ids = set()
        try:
            for document in documents:
                self._validate_document_file(document)
                db.update_document(
                    document.id,
                    client_id=user_id,
                    processing_status="processing",
                    status="uploaded",
                )
                cleared_document_ids.add(document.id)
                self._clear_existing_ingestion(document.id)

            chunks = self.chunking_service.chunk_collection(
                documents=documents,
                persona=persona,
                job=job,
            )
            if not chunks:
                raise ValueError("No text chunks could be created from the document collection")

            chunks_by_document: Dict[str, List[DocumentChunk]] = defaultdict(list)
            for chunk in chunks:
                chunks_by_document[chunk.document_id].append(chunk)

            totals = {
                "chunks_stored": 0,
                "embeddings_generated": 0,
                "vectors_added": 0,
            }

            for document in documents:
                result = self._persist_chunks(
                    document=document,
                    user_id=user_id,
                    chunks=chunks_by_document.get(document.id, []),
                    batch_size=batch_size,
                )
                for key in totals:
                    totals[key] += result[key]

                metadata = self._merge_metadata(
                    document.metadata,
                    {
                        "ingestion": {
                            "mode": "multi",
                            "source": "canonical_ingestion_service",
                            "chunks_created": result["chunks_stored"],
                            "vectors_added": result["vectors_added"],
                        }
                    },
                )
                db.update_document(
                    document.id,
                    client_id=user_id,
                    processing_status="completed",
                    status="processed",
                    metadata=metadata,
                )

            return {
                "success": True,
                "mode": "multi",
                "document_ids": [document.id for document in documents],
                "documents_processed": len(documents),
                **totals,
                "elapsed_seconds": round(time.time() - start_time, 2),
            }

        except Exception as exc:
            for document_id in cleared_document_ids:
                self._cleanup_failed_ingestion(document_id)
            for document in documents:
                db.update_document(
                    document.id,
                    client_id=user_id,
                    processing_status="failed",
                    metadata=self._merge_metadata(
                        document.metadata,
                        {"ingestion": {"mode": "multi", "error": str(exc)}},
                    ),
                )
            return {"success": False, "error": str(exc), "document_ids": [doc.id for doc in documents]}

    def _persist_chunks(
        self,
        document: Document,
        user_id: str,
        chunks: List[DocumentChunk],
        batch_size: int,
    ) -> Dict[str, int]:
        if not chunks:
            return {"chunks_stored": 0, "embeddings_generated": 0, "vectors_added": 0}

        chunk_texts = [self._embedding_text(document, chunk) for chunk in chunks]
        embeddings = self.embedding_service.generate_embeddings_batch(
            chunk_texts,
            batch_size=batch_size,
            show_progress=True,
        )

        chunk_ids: List[str] = []
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = db.store_chunk(
                document_id=document.id,
                chunk_text=chunk.text,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                embedding=embedding,
                char_count=chunk.metadata.get("char_count"),
                word_count=chunk.metadata.get("word_count"),
            )
            chunk_ids.append(chunk_id)

        metadatas = [
            self._vector_metadata(
                document=document,
                user_id=user_id,
                chunk=chunk,
                chunk_id=chunk_id,
            )
            for chunk_id, chunk in zip(chunk_ids, chunks)
        ]
        vector_ids = self.vector_store.add_documents(embeddings, metadatas)

        return {
            "chunks_stored": len(chunk_ids),
            "embeddings_generated": len(embeddings),
            "vectors_added": len(vector_ids),
        }

    def _vector_metadata(
        self,
        document: Document,
        user_id: str,
        chunk: DocumentChunk,
        chunk_id: str,
    ) -> Dict[str, Any]:
        chunk_metadata = dict(chunk.metadata or {})
        document_name = self._document_name(document)
        section_title = chunk_metadata.get("section_title") or chunk_metadata.get("heading") or document_name
        embedding_service = getattr(self, "embedding_service", None)
        upload_date = self._timestamp_value(document.upload_date)
        last_uploaded = self._timestamp_value(document.last_uploaded) or upload_date

        return {
            "chunk_id": chunk_id,
            "document_id": document.id,
            "user_id": user_id,
            "filename": document.filename,
            "document_name": document_name,
            "original_name": document.original_name,
            "file_path": document.file_path,
            "chunk_text": chunk.text,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "section_title": section_title,
            "upload_date": upload_date,
            "last_uploaded": last_uploaded,
            "last_opened": self._timestamp_value(document.last_opened),
            "last_accessed": self._timestamp_value(document.last_accessed),
            "embedding_model": getattr(embedding_service, "model_name", None),
            "embedding_dimension": getattr(embedding_service, "embedding_dim", None),
            "embedding_text_strategy": "document_section_context_v1",
            "metadata": chunk_metadata,
        }

    def _embedding_text(self, document: Document, chunk: DocumentChunk) -> str:
        chunk_metadata = dict(chunk.metadata or {})
        document_name = self._document_name(document)
        section_title = chunk_metadata.get("section_title") or chunk_metadata.get("heading")
        concepts = chunk_metadata.get("key_concepts") or []
        entities = chunk_metadata.get("key_entities") or []

        context_parts = [
            f"Document: {document_name}",
            f"Page: {chunk.page_number}",
        ]
        if section_title:
            context_parts.append(f"Section: {section_title}")
        if concepts:
            context_parts.append(f"Key concepts: {', '.join(str(concept) for concept in concepts[:8])}")
        if entities:
            context_parts.append(f"Key entities: {', '.join(str(entity) for entity in entities[:8])}")

        return "\n".join([*context_parts, "", chunk.text])

    def _clear_existing_ingestion(self, document_id: str) -> None:
        db.delete_chunks_by_document(document_id)
        self.vector_store.remove_document(document_id)

    def _cleanup_failed_ingestion(self, document_id: str) -> None:
        try:
            db.delete_chunks_by_document(document_id)
        except Exception as exc:
            logger.warning("Failed to clean partial chunks for %s: %s", document_id, exc)

        try:
            self.vector_store.remove_document(document_id)
        except Exception as exc:
            logger.warning("Failed to clean partial vectors for %s: %s", document_id, exc)

    def _validate_document_file(self, document: Document) -> None:
        path = Path(document.file_path)
        if not path.exists():
            raise FileNotFoundError(f"Document file not found: {path}")

    def _merge_metadata(self, existing: Optional[Dict[str, Any]], new_metadata: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(existing or {})
        merged.update(new_metadata)
        return merged

    def _document_name(self, document: Document) -> str:
        return document.original_name or document.filename or document.id

    def _timestamp_value(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)


_ingestion_service_instance: Optional[DocumentIngestionService] = None


def get_ingestion_service() -> DocumentIngestionService:
    global _ingestion_service_instance
    if _ingestion_service_instance is None:
        _ingestion_service_instance = DocumentIngestionService()
    return _ingestion_service_instance
