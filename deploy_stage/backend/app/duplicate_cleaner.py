#!/usr/bin/env python3
"""
Duplicate PDF Cleaner for Adobe Hackathon System
Removes duplicate PDFs with different IDs based on file content hash
"""

import hashlib
import os
from pathlib import Path
from typing import List, Dict, Set
import logging
from .database import DocumentDatabase

logger = logging.getLogger(__name__)

class DuplicatePDFCleaner:
    def __init__(self, db: DocumentDatabase, docs_dir: Path):
        self.db = db
        self.docs_dir = Path(docs_dir)
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file content"""
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash for {file_path}: {e}")
            return None
    
    def get_file_size(self, file_path: Path) -> int:
        """Get file size in bytes"""
        try:
            return file_path.stat().st_size
        except Exception as e:
            logger.error(f"Error getting size for {file_path}: {e}")
            return 0
    
    def find_duplicates(self) -> Dict[str, List[Dict]]:
        """Find duplicate PDFs based on file hash and size"""
        print("🔍 Scanning for duplicate PDFs...")
        
        # Get all documents from database
        all_documents = self.db.get_all_documents()
        
        # Group documents by hash and size
        file_groups = {}
        processed_files = set()
        
        for doc in all_documents:
            try:
                # Construct file path
                file_path = Path(doc.file_path)
                if not file_path.is_absolute():
                    file_path = self.docs_dir.parent / file_path
                
                # Skip if file doesn't exist - but don't delete from database yet
                if not file_path.exists():
                    print(f"⚠️ File not found: {file_path}")
                    # Try alternative file path with filename
                    alt_file_path = self.docs_dir / doc.filename
                    if alt_file_path.exists():
                        print(f"✅ Found file at alternative path: {alt_file_path}")
                        file_path = alt_file_path
                    else:
                        print(f"⚠️ File not found at alternative path either: {alt_file_path}")
                        print(f"🔍 Skipping orphaned entry (not deleting): {doc.original_name}")
                        continue
                
                # Skip if already processed (same physical file)
                abs_path = str(file_path.absolute())
                if abs_path in processed_files:
                    continue
                processed_files.add(abs_path)
                
                # Calculate file hash and size
                file_hash = self.calculate_file_hash(file_path)
                file_size = self.get_file_size(file_path)
                
                if not file_hash:
                    continue
                
                # Create unique key based on hash and size
                key = f"{file_hash}_{file_size}"
                
                if key not in file_groups:
                    file_groups[key] = []
                
                file_groups[key].append({
                    'id': doc.id,
                    'original_name': doc.original_name,
                    'file_path': str(file_path),
                    'file_size': file_size,
                    'hash': file_hash,
                    'upload_date': doc.upload_date,
                    'last_opened': doc.last_opened,
                    'open_count': getattr(doc, 'open_count', 0) or 0
                })
                
            except Exception as e:
                logger.error(f"Error processing document {doc.id}: {e}")
                continue
        
        # Filter to only groups with duplicates
        duplicates = {k: v for k, v in file_groups.items() if len(v) > 1}
        
        print(f"📊 Found {len(duplicates)} groups of duplicate files")
        for key, group in duplicates.items():
            print(f"  📁 Group {key[:8]}... has {len(group)} duplicates:")
            for doc in group:
                print(f"    - {doc['original_name']} (ID: {doc['id'][:8]}...)")
        
        return duplicates
    
    def remove_duplicates(self, duplicates: Dict[str, List[Dict]]) -> Dict[str, int]:
        """Remove duplicate PDFs, keeping the most recently used one"""
        stats = {
            'groups_processed': 0,
            'files_removed': 0,
            'files_kept': 0,
            'errors': 0
        }
        
        for key, group in duplicates.items():
            try:
                stats['groups_processed'] += 1
                
                # Sort by priority: last_opened (desc), open_count (desc), upload_date (desc)
                def sort_priority(doc):
                    last_opened = doc['last_opened'] or '1900-01-01'
                    open_count = doc['open_count'] or 0
                    upload_date = doc['upload_date'] or '1900-01-01'
                    return (last_opened, open_count, upload_date)
                
                sorted_group = sorted(group, key=sort_priority, reverse=True)
                
                # Keep the first one (highest priority)
                keep_doc = sorted_group[0]
                remove_docs = sorted_group[1:]
                
                print(f"📁 Processing group {key[:8]}...")
                print(f"  ✅ Keeping: {keep_doc['original_name']} (ID: {keep_doc['id'][:8]}...)")
                
                # Safety check: don't remove more than 50% of documents
                total_docs = len(all_documents)
                max_removable = max(1, total_docs // 2)  # At least 1, but no more than 50%

                if len(remove_docs) > max_removable:
                    print(f"⚠️ Safety check: Would remove {len(remove_docs)} docs, but limiting to {max_removable}")
                    remove_docs = remove_docs[:max_removable]

                # Remove duplicates
                for doc in remove_docs:
                    try:
                        print(f"  🗑️ Removing: {doc['original_name']} (ID: {doc['id'][:8]}...)")

                        # Remove from database (soft delete)
                        success = self.db.delete_document(doc['id'], soft_delete=True)
                        if success:
                            stats['files_removed'] += 1
                            
                            # Remove physical file if it's different from the kept one
                            doc_path = Path(doc['file_path'])
                            keep_path = Path(keep_doc['file_path'])
                            
                            if doc_path.absolute() != keep_path.absolute() and doc_path.exists():
                                try:
                                    doc_path.unlink()
                                    print(f"    🗑️ Deleted physical file: {doc_path.name}")
                                except Exception as e:
                                    print(f"    ⚠️ Could not delete physical file: {e}")
                        else:
                            print(f"    ❌ Failed to remove from database")
                            stats['errors'] += 1
                            
                    except Exception as e:
                        logger.error(f"Error removing duplicate {doc['id']}: {e}")
                        stats['errors'] += 1
                
                stats['files_kept'] += 1
                
            except Exception as e:
                logger.error(f"Error processing group {key}: {e}")
                stats['errors'] += 1
        
        return stats
    
    def clean_duplicates(self) -> Dict[str, int]:
        """Main method to find and remove duplicates"""
        print("🧹 Starting duplicate PDF cleanup...")
        
        try:
            # Find duplicates
            duplicates = self.find_duplicates()
            
            if not duplicates:
                print("✅ No duplicate PDFs found!")
                return {
                    'groups_processed': 0,
                    'files_removed': 0,
                    'files_kept': 0,
                    'errors': 0
                }
            
            # Remove duplicates
            stats = self.remove_duplicates(duplicates)
            
            print(f"🎉 Duplicate cleanup completed!")
            print(f"  📊 Groups processed: {stats['groups_processed']}")
            print(f"  🗑️ Files removed: {stats['files_removed']}")
            print(f"  ✅ Files kept: {stats['files_kept']}")
            print(f"  ❌ Errors: {stats['errors']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error during duplicate cleanup: {e}")
            return {
                'groups_processed': 0,
                'files_removed': 0,
                'files_kept': 0,
                'errors': 1
            }

def run_duplicate_cleanup(db: DocumentDatabase, docs_dir: Path) -> Dict[str, int]:
    """Convenience function to run duplicate cleanup"""
    cleaner = DuplicatePDFCleaner(db, docs_dir)
    return cleaner.clean_duplicates()
