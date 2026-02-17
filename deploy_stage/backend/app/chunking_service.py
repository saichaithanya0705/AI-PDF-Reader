"""
Document Chunking Service for RAG
Splits PDF documents into smaller chunks for embedding and vector search
"""
from typing import List, Dict, Any
import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentChunk:
    """Represents a chunk of a document"""
    text: str
    page_number: int
    chunk_index: int
    document_id: str
    metadata: Dict[str, Any]


class ChunkingService:
    """Service for chunking PDF documents using recursive character splitting"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100
    ):
        """
        Initialize the chunking service
        
        Args:
            chunk_size: Target size for each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
            min_chunk_size: Minimum size for a chunk to be created
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        
        # Separators for recursive splitting (from most important to least)
        self.separators = [
            "\n\n",  # Paragraph breaks
            "\n",    # Line breaks
            ". ",    # Sentences
            "! ",    # Exclamations
            "? ",    # Questions
            "; ",    # Semicolons
            ", ",    # Commas
            " ",     # Words
            ""       # Characters
        ]
    
    def chunk_document(
        self,
        pdf_path: str,
        document_id: str
    ) -> List[DocumentChunk]:
        """
        Chunk a PDF document into smaller pieces
        
        Args:
            pdf_path: Path to the PDF file
            document_id: Unique identifier for the document
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        chunk_index = 0
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            num_pages = len(doc)
            
            # Process each page
            for page_num in range(num_pages):
                page = doc[page_num]
                text = page.get_text()
                
                if not text.strip():
                    continue
                
                # Split page text into chunks
                page_chunks = self._split_text(
                    text,
                    page_num + 1,  # 1-indexed page numbers
                    document_id,
                    chunk_index
                )
                
                chunks.extend(page_chunks)
                chunk_index += len(page_chunks)
            
            doc.close()
            
            print(f"✅ Chunked document {document_id}: {len(chunks)} chunks from {num_pages} pages")
            
        except Exception as e:
            print(f"❌ Error chunking document {document_id}: {str(e)}")
            raise
        
        return chunks
    
    def _split_text(
        self,
        text: str,
        page_number: int,
        document_id: str,
        start_index: int
    ) -> List[DocumentChunk]:
        """
        Recursively split text into chunks
        
        Args:
            text: Text to split
            page_number: Page number this text came from
            document_id: Document identifier
            start_index: Starting chunk index
            
        Returns:
            List of DocumentChunk objects
        """
        chunks = []
        
        # If text is small enough, return as single chunk
        if len(text) <= self.chunk_size:
            if len(text.strip()) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    text=text.strip(),
                    page_number=page_number,
                    chunk_index=start_index,
                    document_id=document_id,
                    metadata={
                        'char_count': len(text),
                        'word_count': len(text.split())
                    }
                ))
            return chunks
        
        # Try to split using separators
        for separator in self.separators:
            if separator in text:
                splits = text.split(separator)
                
                # Rebuild chunks respecting chunk_size and overlap
                current_chunk = []
                current_size = 0
                
                for split in splits:
                    split_size = len(split) + len(separator)
                    
                    # If adding this split exceeds chunk_size, save current chunk
                    if current_size + split_size > self.chunk_size and current_chunk:
                        chunk_text = separator.join(current_chunk)
                        if len(chunk_text.strip()) >= self.min_chunk_size:
                            chunks.append(DocumentChunk(
                                text=chunk_text.strip(),
                                page_number=page_number,
                                chunk_index=start_index + len(chunks),
                                document_id=document_id,
                                metadata={
                                    'char_count': len(chunk_text),
                                    'word_count': len(chunk_text.split())
                                }
                            ))
                        
                        # Start new chunk with overlap
                        # Keep last few splits for overlap
                        overlap_text = separator.join(current_chunk[-2:]) if len(current_chunk) >= 2 else ""
                        if overlap_text:
                            current_chunk = [overlap_text, split] if split.strip() else [overlap_text]
                            current_size = len(overlap_text) + split_size
                        else:
                            current_chunk = [split] if split.strip() else []
                            current_size = split_size
                    else:
                        # Add split to current chunk
                        if split.strip():
                            current_chunk.append(split)
                            current_size += split_size
                
                # Add remaining chunk
                if current_chunk:
                    chunk_text = separator.join(current_chunk)
                    if len(chunk_text.strip()) >= self.min_chunk_size:
                        chunks.append(DocumentChunk(
                            text=chunk_text.strip(),
                            page_number=page_number,
                            chunk_index=start_index + len(chunks),
                            document_id=document_id,
                            metadata={
                                'char_count': len(chunk_text),
                                'word_count': len(chunk_text.split())
                            }
                        ))
                
                return chunks
        
        # Fallback: split by character count if no separator worked
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk_text = text[i:i + self.chunk_size]
            if len(chunk_text.strip()) >= self.min_chunk_size:
                chunks.append(DocumentChunk(
                    text=chunk_text.strip(),
                    page_number=page_number,
                    chunk_index=start_index + len(chunks),
                    document_id=document_id,
                    metadata={
                        'char_count': len(chunk_text),
                        'word_count': len(chunk_text.split())
                    }
                ))
        
        return chunks


# Global instance
chunking_service = ChunkingService(
    chunk_size=1000,
    chunk_overlap=200,
    min_chunk_size=100
)
