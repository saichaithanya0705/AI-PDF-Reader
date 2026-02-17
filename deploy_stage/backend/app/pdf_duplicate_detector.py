#!/usr/bin/env python3
"""
Advanced PDF Duplicate Detection System
Detects duplicates using multiple techniques: filename, content hash, PDF metadata, and text content
"""

import hashlib
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import PyPDF2
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class PDFDuplicateDetector:
    """Advanced PDF duplicate detection using multiple techniques"""
    
    def __init__(self, db_path: str, docs_dir: Path):
        self.db_path = db_path
        self.docs_dir = Path(docs_dir)
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return ""
    
    def extract_pdf_metadata(self, file_path: Path) -> Dict:
        """Extract PDF metadata for comparison"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata or {}
                
                return {
                    'title': metadata.get('/Title', ''),
                    'author': metadata.get('/Author', ''),
                    'subject': metadata.get('/Subject', ''),
                    'creator': metadata.get('/Creator', ''),
                    'producer': metadata.get('/Producer', ''),
                    'creation_date': metadata.get('/CreationDate', ''),
                    'modification_date': metadata.get('/ModDate', ''),
                    'page_count': len(pdf_reader.pages)
                }
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {e}")
            return {}
    
    def extract_pdf_text_sample(self, file_path: Path, max_chars: int = 1000) -> str:
        """Extract first few characters of PDF text for comparison"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                
                # Extract text from first few pages
                for page_num in range(min(3, len(pdf_reader.pages))):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text()
                    if len(text) > max_chars:
                        break
                
                # Clean and normalize text
                text = re.sub(r'\s+', ' ', text.strip())
                return text[:max_chars]
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def normalize_filename(self, filename: str) -> str:
        """Normalize filename for comparison (remove ID prefix, extensions, etc.)"""
        # Remove UUID prefix pattern (e.g., "uuid_filename.pdf" -> "filename")
        normalized = re.sub(r'^[a-f0-9-]{36}_', '', filename, flags=re.IGNORECASE)
        
        # Remove file extension
        normalized = re.sub(r'\.(pdf|PDF)$', '', normalized)
        
        # Normalize whitespace and special characters
        normalized = re.sub(r'[_\-\s]+', ' ', normalized)
        normalized = normalized.strip().lower()
        
        return normalized
    
    def are_pdfs_identical(self, file1_path: Path, file2_path: Path) -> Dict[str, bool]:
        """Compare two PDFs using multiple techniques"""
        comparison = {
            'file_hash_match': False,
            'size_match': False,
            'metadata_match': False,
            'text_sample_match': False,
            'filename_similar': False
        }
        
        try:
            # File size comparison
            if file1_path.exists() and file2_path.exists():
                size1 = file1_path.stat().st_size
                size2 = file2_path.stat().st_size
                comparison['size_match'] = size1 == size2
                
                # File hash comparison (most reliable)
                hash1 = self.calculate_file_hash(file1_path)
                hash2 = self.calculate_file_hash(file2_path)
                comparison['file_hash_match'] = hash1 == hash2 and hash1 != ""
                
                # Filename similarity
                name1 = self.normalize_filename(file1_path.name)
                name2 = self.normalize_filename(file2_path.name)
                comparison['filename_similar'] = name1 == name2
                
                # If file hashes match, they're definitely identical
                if comparison['file_hash_match']:
                    comparison['metadata_match'] = True
                    comparison['text_sample_match'] = True
                else:
                    # Additional checks for similar files
                    metadata1 = self.extract_pdf_metadata(file1_path)
                    metadata2 = self.extract_pdf_metadata(file2_path)
                    
                    # Compare key metadata fields
                    metadata_matches = 0
                    metadata_fields = ['title', 'author', 'page_count', 'creation_date']
                    for field in metadata_fields:
                        if metadata1.get(field) and metadata2.get(field):
                            if metadata1[field] == metadata2[field]:
                                metadata_matches += 1
                    
                    comparison['metadata_match'] = metadata_matches >= 2
                    
                    # Text sample comparison
                    text1 = self.extract_pdf_text_sample(file1_path)
                    text2 = self.extract_pdf_text_sample(file2_path)
                    comparison['text_sample_match'] = text1 == text2 and text1 != ""
                    
        except Exception as e:
            logger.error(f"Error comparing PDFs {file1_path} and {file2_path}: {e}")
        
        return comparison
    
    def is_duplicate(self, comparison: Dict[str, bool]) -> bool:
        """Determine if files are duplicates based on comparison results"""
        # Identical file hash = definite duplicate
        if comparison['file_hash_match']:
            return True
        
        # Multiple indicators suggest duplicate
        indicators = [
            comparison['size_match'],
            comparison['metadata_match'],
            comparison['text_sample_match'],
            comparison['filename_similar']
        ]
        
        # Need at least 3 out of 4 indicators for duplicate
        return sum(indicators) >= 3
    
    def find_duplicates_in_database(self) -> List[Dict]:
        """Find all duplicate groups in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all active documents
        cursor.execute('''
            SELECT id, original_name, filename, file_size, file_hash, upload_date, last_opened
            FROM documents WHERE status != "deleted"
            ORDER BY upload_date ASC
        ''')
        
        documents = []
        for row in cursor.fetchall():
            documents.append({
                'id': row[0],
                'original_name': row[1],
                'filename': row[2],
                'file_size': row[3],
                'file_hash': row[4],
                'upload_date': row[5],
                'last_opened': row[6],
                'file_path': self.docs_dir / row[2]
            })
        
        conn.close()
        
        # Group by file hash first (most reliable)
        hash_groups = {}
        for doc in documents:
            if doc['file_hash']:
                if doc['file_hash'] not in hash_groups:
                    hash_groups[doc['file_hash']] = []
                hash_groups[doc['file_hash']].append(doc)
        
        # Find duplicate groups
        duplicate_groups = []
        for hash_val, docs in hash_groups.items():
            if len(docs) > 1:
                # Sort by upload date (keep earliest) and last_opened (prefer opened ones)
                docs.sort(key=lambda x: (
                    x['last_opened'] is None,  # Put opened docs first
                    x['upload_date']  # Then by earliest upload date
                ))
                
                duplicate_groups.append({
                    'hash': hash_val,
                    'keep': docs[0],  # Keep the first (earliest uploaded or last opened)
                    'remove': docs[1:],  # Remove the rest
                    'total_count': len(docs)
                })
        
        return duplicate_groups
