"""
Robust PDF Comparison System
High-performance PDF comparison using multiple techniques for duplicate detection
Reusable for merge functionality
"""

import hashlib
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import time
from dataclasses import dataclass

@dataclass
class PDFComparisonResult:
    """Result of PDF comparison"""
    is_identical: bool
    similarity_score: float  # 0.0 to 1.0
    comparison_method: str
    comparison_time_ms: float
    file1_hash: str
    file2_hash: str
    size_match: bool
    metadata: Dict[str, Any]

class PDFComparator:
    """
    High-performance PDF comparison system using multiple techniques:
    1. Fast size comparison (O(1))
    2. Binary hash comparison with recursive chunking
    3. Content-based comparison for merge compatibility
    """
    
    def __init__(self, chunk_size: int = 8192):
        self.chunk_size = chunk_size
        self.comparison_cache = {}  # Cache for repeated comparisons
    
    def compare_pdfs(self, file1_path: str, file2_path: str, 
                    deep_comparison: bool = False) -> PDFComparisonResult:
        """
        Compare two PDF files using optimized recursive binary search approach
        
        Args:
            file1_path: Path to first PDF
            file2_path: Path to second PDF  
            deep_comparison: Whether to perform deep content analysis
            
        Returns:
            PDFComparisonResult with detailed comparison data
        """
        start_time = time.time()
        
        # Convert to Path objects
        path1 = Path(file1_path)
        path2 = Path(file2_path)
        
        # Quick validation
        if not path1.exists() or not path2.exists():
            return PDFComparisonResult(
                is_identical=False,
                similarity_score=0.0,
                comparison_method="file_not_found",
                comparison_time_ms=0.0,
                file1_hash="",
                file2_hash="",
                size_match=False,
                metadata={"error": "One or both files not found"}
            )
        
        # Check cache first
        cache_key = f"{path1.stat().st_mtime}_{path2.stat().st_mtime}_{path1.stat().st_size}_{path2.stat().st_size}"
        if cache_key in self.comparison_cache:
            cached_result = self.comparison_cache[cache_key]
            cached_result.comparison_time_ms = (time.time() - start_time) * 1000
            return cached_result
        
        # Step 1: Fast size comparison (O(1))
        size1 = path1.stat().st_size
        size2 = path2.stat().st_size
        size_match = size1 == size2
        
        if not size_match:
            result = PDFComparisonResult(
                is_identical=False,
                similarity_score=0.0,
                comparison_method="size_mismatch",
                comparison_time_ms=(time.time() - start_time) * 1000,
                file1_hash="",
                file2_hash="",
                size_match=False,
                metadata={"size1": size1, "size2": size2}
            )
            self.comparison_cache[cache_key] = result
            return result
        
        # Step 2: Recursive binary hash comparison
        if deep_comparison:
            result = self._deep_binary_comparison(path1, path2, start_time)
        else:
            result = self._fast_hash_comparison(path1, path2, start_time)
        
        # Cache the result
        self.comparison_cache[cache_key] = result
        return result
    
    def _fast_hash_comparison(self, path1: Path, path2: Path, start_time: float) -> PDFComparisonResult:
        """Fast hash-based comparison using SHA256"""
        try:
            hash1 = self._calculate_file_hash(path1)
            hash2 = self._calculate_file_hash(path2)
            
            is_identical = hash1 == hash2
            similarity_score = 1.0 if is_identical else 0.0
            
            return PDFComparisonResult(
                is_identical=is_identical,
                similarity_score=similarity_score,
                comparison_method="sha256_hash",
                comparison_time_ms=(time.time() - start_time) * 1000,
                file1_hash=hash1,
                file2_hash=hash2,
                size_match=True,
                metadata={"algorithm": "SHA256"}
            )
            
        except Exception as e:
            return PDFComparisonResult(
                is_identical=False,
                similarity_score=0.0,
                comparison_method="hash_error",
                comparison_time_ms=(time.time() - start_time) * 1000,
                file1_hash="",
                file2_hash="",
                size_match=True,
                metadata={"error": str(e)}
            )
    
    def _deep_binary_comparison(self, path1: Path, path2: Path, start_time: float) -> PDFComparisonResult:
        """
        Deep binary comparison using recursive binary search approach
        Optimized for large files by comparing chunks recursively
        """
        try:
            # First do fast hash comparison
            hash_result = self._fast_hash_comparison(path1, path2, start_time)
            
            if hash_result.is_identical:
                hash_result.comparison_method = "deep_binary_identical"
                return hash_result
            
            # If hashes don't match, do recursive binary comparison for similarity
            similarity_score = self._recursive_binary_similarity(path1, path2)
            
            return PDFComparisonResult(
                is_identical=similarity_score >= 0.99,
                similarity_score=similarity_score,
                comparison_method="recursive_binary_search",
                comparison_time_ms=(time.time() - start_time) * 1000,
                file1_hash=hash_result.file1_hash,
                file2_hash=hash_result.file2_hash,
                size_match=True,
                metadata={
                    "chunks_compared": self._chunks_compared,
                    "algorithm": "recursive_binary_similarity"
                }
            )
            
        except Exception as e:
            return PDFComparisonResult(
                is_identical=False,
                similarity_score=0.0,
                comparison_method="deep_comparison_error",
                comparison_time_ms=(time.time() - start_time) * 1000,
                file1_hash="",
                file2_hash="",
                size_match=True,
                metadata={"error": str(e)}
            )
    
    def _recursive_binary_similarity(self, path1: Path, path2: Path) -> float:
        """
        Recursive binary search similarity calculation
        Divides file into chunks and compares recursively for efficiency
        """
        self._chunks_compared = 0
        file_size = path1.stat().st_size
        
        with open(path1, 'rb') as f1, open(path2, 'rb') as f2:
            return self._compare_chunks_recursive(f1, f2, 0, file_size, file_size)
    
    def _compare_chunks_recursive(self, f1, f2, start: int, end: int, total_size: int) -> float:
        """
        Recursive chunk comparison using binary search approach
        """
        self._chunks_compared += 1
        
        # Base case: chunk too small
        if end - start < self.chunk_size:
            f1.seek(start)
            f2.seek(start)
            chunk1 = f1.read(end - start)
            chunk2 = f2.read(end - start)
            return 1.0 if chunk1 == chunk2 else 0.0
        
        # Divide and conquer approach
        mid = (start + end) // 2
        
        # Compare middle chunk first (most likely to differ)
        f1.seek(mid)
        f2.seek(mid)
        chunk_size = min(self.chunk_size, end - mid)
        chunk1 = f1.read(chunk_size)
        chunk2 = f2.read(chunk_size)
        
        if chunk1 != chunk2:
            # If middle differs, check both halves
            left_similarity = self._compare_chunks_recursive(f1, f2, start, mid, total_size)
            right_similarity = self._compare_chunks_recursive(f1, f2, mid + chunk_size, end, total_size)
            
            # Weight by chunk size
            left_weight = (mid - start) / total_size
            right_weight = (end - mid - chunk_size) / total_size
            middle_weight = chunk_size / total_size
            
            return (left_similarity * left_weight + 
                   right_similarity * right_weight + 
                   0.0 * middle_weight)
        else:
            # If middle matches, recursively check both halves
            left_similarity = self._compare_chunks_recursive(f1, f2, start, mid, total_size)
            right_similarity = self._compare_chunks_recursive(f1, f2, mid + chunk_size, end, total_size)
            
            # Weight by chunk size
            left_weight = (mid - start) / total_size
            right_weight = (end - mid - chunk_size) / total_size
            middle_weight = chunk_size / total_size
            
            return (left_similarity * left_weight + 
                   right_similarity * right_weight + 
                   1.0 * middle_weight)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file efficiently"""
        hash_sha256 = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            # Read in chunks for memory efficiency
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                hash_sha256.update(chunk)
        
        return hash_sha256.hexdigest()
    
    def find_duplicate_by_hash(self, target_file: str, file_list: list) -> Optional[str]:
        """
        Find duplicate file in list using optimized hash comparison
        Returns path of duplicate file if found, None otherwise
        """
        if not os.path.exists(target_file):
            return None
        
        target_hash = self._calculate_file_hash(Path(target_file))
        target_size = os.path.getsize(target_file)
        
        for file_path in file_list:
            if not os.path.exists(file_path):
                continue
            
            # Quick size check first
            if os.path.getsize(file_path) != target_size:
                continue
            
            # Hash comparison
            file_hash = self._calculate_file_hash(Path(file_path))
            if file_hash == target_hash:
                return file_path
        
        return None
    
    def clear_cache(self):
        """Clear comparison cache"""
        self.comparison_cache.clear()

# Global comparator instance
pdf_comparator = PDFComparator()
