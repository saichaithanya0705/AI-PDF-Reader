"""
Document chunking service for RAG.

This module is the adapter layer between the PDF-specific algorithms and the
generic embedding/vector pipeline:
- single PDF uploads use the high-performance outline/section extractor
- multi PDF uploads use the cross-document semantic PDF brain
- page text splitting remains as a fallback when an algorithm yields no sections
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import logging

import fitz  # PyMuPDF

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a document."""

    text: str
    page_number: int
    chunk_index: int
    document_id: str
    metadata: Dict[str, Any]


class ChunkingService:
    """Canonical chunking service for PDF documents."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.separators = [
            "\n\n",
            "\n",
            ". ",
            "! ",
            "? ",
            "; ",
            ", ",
            " ",
            "",
        ]

    def chunk_document(
        self,
        pdf_path: str,
        document_id: str,
        document_name: Optional[str] = None,
        mode: str = "single",
        persona: Optional[str] = None,
        job: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """Chunk one PDF using the single-PDF algorithm."""
        if mode == "multi":
            logger.info("chunk_document received mode=multi for one file; using single algorithm")

        return self.chunk_single_pdf(
            pdf_path=pdf_path,
            document_id=document_id,
            document_name=document_name,
            persona=persona,
            job=job,
        )

    def chunk_single_pdf(
        self,
        pdf_path: str,
        document_id: str,
        document_name: Optional[str] = None,
        persona: Optional[str] = None,
        job: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """Chunk a single PDF through the high-performance PDF section extractor."""
        chunks: List[DocumentChunk] = []
        pdf_name = document_name or Path(pdf_path).name

        try:
            from .utils.process_pdfs import extract_sections

            sections = extract_sections(str(pdf_path), document_id)
            chunk_index = 0

            for section in sections:
                title = (getattr(section, "section_title", "") or "").strip()
                content = (getattr(section, "content", "") or "").strip()
                text = f"{title}\n\n{content}".strip() if title else content
                if not text:
                    continue

                metadata = {
                    "document_name": pdf_name,
                    "filename": pdf_name,
                    "section_title": title or "Untitled",
                    "level": getattr(section, "level", None),
                    "source_algorithm": "single_pdf_outline",
                    "persona": persona,
                    "job": job,
                }

                section_chunks = self._split_text(
                    text=text,
                    page_number=self._normalize_page_number(getattr(section, "page_number", 0), zero_based=True),
                    document_id=document_id,
                    start_index=chunk_index,
                    base_metadata=metadata,
                )
                chunks.extend(section_chunks)
                chunk_index += len(section_chunks)

            if chunks:
                logger.info("Chunked %s with single PDF algorithm into %s chunks", document_id, len(chunks))
                return chunks

            logger.warning("Single PDF algorithm returned no chunks for %s; falling back to page text", document_id)

        except Exception as exc:
            logger.warning("Single PDF algorithm failed for %s; falling back to page text: %s", document_id, exc)

        return self._chunk_pages(
            pdf_path=pdf_path,
            document_id=document_id,
            document_name=pdf_name,
            source_algorithm="page_text_fallback",
        )

    def chunk_collection(
        self,
        documents: Iterable[Any],
        persona: Optional[str] = None,
        job: Optional[str] = None,
    ) -> List[DocumentChunk]:
        """
        Chunk a collection through the multi-PDF semantic algorithm.

        The documents can be database Document objects or any objects with
        id, file_path, filename/original_name fields.
        """
        document_list = list(documents)
        if not document_list:
            return []

        try:
            from .utils.intelligent_pdf_brain import IntelligentPDFBrain

            brain = IntelligentPDFBrain()
            section_records: List[Tuple[Any, Any]] = []

            for document in document_list:
                path = Path(document.file_path)
                pdf_doc = fitz.open(str(path))
                try:
                    sections = brain.extract_semantic_content(pdf_doc)
                finally:
                    pdf_doc.close()

                doc_name = self._document_name(document)
                for section in sections:
                    section.document = doc_name
                    if persona and job:
                        try:
                            section.relevance_score = brain.calculate_enhanced_relevance_score(section, persona, job)
                        except Exception as exc:
                            logger.debug("Relevance scoring failed for %s: %s", doc_name, exc)
                    section_records.append((document, section))

            if not section_records:
                logger.warning("Multi PDF algorithm returned no sections; using single-PDF fallback for each document")
                return self._chunk_collection_with_single_fallback(document_list, persona, job)

            sections_only = [record[1] for record in section_records]
            try:
                graph = brain.build_knowledge_graph(sections_only)
                brain._calculate_graph_importance(sections_only, graph)
            except Exception as exc:
                logger.debug("Knowledge graph importance calculation skipped: %s", exc)

            chunks: List[DocumentChunk] = []
            next_index_by_doc: Dict[str, int] = {}

            for document, section in section_records:
                document_id = document.id
                doc_name = self._document_name(document)
                title = (section.section_title or "").strip()
                content = (section.content or "").strip()
                text = f"{title}\n\n{content}".strip() if title else content
                if not text:
                    continue

                start_index = next_index_by_doc.get(document_id, 0)
                metadata = {
                    "document_name": doc_name,
                    "filename": doc_name,
                    "section_title": title or "Untitled",
                    "source_algorithm": "multi_pdf_semantic_brain",
                    "persona": persona,
                    "job": job,
                    "relevance_score": float(section.relevance_score or 0.0),
                    "importance_score": float(section.importance_score or 0.0),
                    "semantic_cluster": int(section.semantic_cluster or -1),
                    "key_entities": list(section.key_entities or []),
                    "key_concepts": list(section.key_concepts or []),
                }

                section_chunks = self._split_text(
                    text=text,
                    page_number=self._normalize_page_number(section.page_number, zero_based=False),
                    document_id=document_id,
                    start_index=start_index,
                    base_metadata=metadata,
                )
                chunks.extend(section_chunks)
                next_index_by_doc[document_id] = start_index + len(section_chunks)

            if chunks:
                logger.info(
                    "Chunked %s documents with multi PDF algorithm into %s chunks",
                    len(document_list),
                    len(chunks),
                )
                return chunks

            return self._chunk_collection_with_single_fallback(document_list, persona, job)

        except Exception as exc:
            logger.warning("Multi PDF algorithm failed; using single-PDF fallback: %s", exc)
            return self._chunk_collection_with_single_fallback(document_list, persona, job)

    def _chunk_collection_with_single_fallback(
        self,
        documents: Iterable[Any],
        persona: Optional[str],
        job: Optional[str],
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        for document in documents:
            chunks.extend(
                self.chunk_single_pdf(
                    pdf_path=document.file_path,
                    document_id=document.id,
                    document_name=self._document_name(document),
                    persona=persona,
                    job=job,
                )
            )
        return chunks

    def _chunk_pages(
        self,
        pdf_path: str,
        document_id: str,
        document_name: str,
        source_algorithm: str,
    ) -> List[DocumentChunk]:
        chunks: List[DocumentChunk] = []
        chunk_index = 0

        doc = fitz.open(pdf_path)
        try:
            for page_num in range(len(doc)):
                text = doc[page_num].get_text()
                if not text.strip():
                    continue

                page_chunks = self._split_text(
                    text=text,
                    page_number=page_num + 1,
                    document_id=document_id,
                    start_index=chunk_index,
                    base_metadata={
                        "document_name": document_name,
                        "filename": document_name,
                        "section_title": f"Page {page_num + 1}",
                        "source_algorithm": source_algorithm,
                    },
                )
                chunks.extend(page_chunks)
                chunk_index += len(page_chunks)
        finally:
            doc.close()

        logger.info("Chunked %s with page fallback into %s chunks", document_id, len(chunks))
        return chunks

    def _split_text(
        self,
        text: str,
        page_number: int,
        document_id: str,
        start_index: int,
        base_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[DocumentChunk]:
        """Recursively split text into chunks."""
        chunks: List[DocumentChunk] = []
        base_metadata = base_metadata or {}

        if len(text) <= self.chunk_size:
            self._append_chunk(chunks, text, page_number, document_id, start_index, base_metadata)
            return chunks

        for separator in self.separators:
            if separator in text:
                splits = text.split(separator)
                current_chunk: List[str] = []
                current_size = 0

                for split in splits:
                    split_size = len(split) + len(separator)

                    if current_size + split_size > self.chunk_size and current_chunk:
                        chunk_text = separator.join(current_chunk)
                        self._append_chunk(
                            chunks,
                            chunk_text,
                            page_number,
                            document_id,
                            start_index + len(chunks),
                            base_metadata,
                        )

                        overlap_text = separator.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ""
                        if overlap_text:
                            current_chunk = [overlap_text, split] if split.strip() else [overlap_text]
                            current_size = len(overlap_text) + split_size
                        else:
                            current_chunk = [split] if split.strip() else []
                            current_size = split_size
                    elif split.strip():
                        current_chunk.append(split)
                        current_size += split_size

                if current_chunk:
                    self._append_chunk(
                        chunks,
                        separator.join(current_chunk),
                        page_number,
                        document_id,
                        start_index + len(chunks),
                        base_metadata,
                    )

                return chunks

        step = max(1, self.chunk_size - self.chunk_overlap)
        for i in range(0, len(text), step):
            self._append_chunk(
                chunks,
                text[i : i + self.chunk_size],
                page_number,
                document_id,
                start_index + len(chunks),
                base_metadata,
            )

        return chunks

    def _append_chunk(
        self,
        chunks: List[DocumentChunk],
        text: str,
        page_number: int,
        document_id: str,
        chunk_index: int,
        base_metadata: Dict[str, Any],
    ) -> None:
        chunk_text = text.strip()
        if len(chunk_text) < self.min_chunk_size:
            return

        metadata = dict(base_metadata)
        metadata.update(
            {
                "char_count": len(chunk_text),
                "word_count": len(chunk_text.split()),
            }
        )
        chunks.append(
            DocumentChunk(
                text=chunk_text,
                page_number=page_number,
                chunk_index=chunk_index,
                document_id=document_id,
                metadata=metadata,
            )
        )

    def _normalize_page_number(self, page_number: Any, zero_based: bool) -> int:
        try:
            page = int(page_number)
        except (TypeError, ValueError):
            page = 0 if zero_based else 1

        if zero_based:
            return max(1, page + 1)
        return max(1, page)

    def _document_name(self, document: Any) -> str:
        return (
            getattr(document, "original_name", None)
            or getattr(document, "filename", None)
            or getattr(document, "id", "Document")
        )


chunking_service = ChunkingService(
    chunk_size=1000,
    chunk_overlap=200,
    min_chunk_size=100,
)
