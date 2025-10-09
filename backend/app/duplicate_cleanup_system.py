#!/usr/bin/env python3
"""
Duplicate Cleanup System
Removes duplicate PDFs while preserving the best copy (earliest upload, latest access)
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
try:
    from .pdf_duplicate_detector import PDFDuplicateDetector
    from .database import db
except ImportError:
    from pdf_duplicate_detector import PDFDuplicateDetector
    from database import db

logger = logging.getLogger(__name__)

class DuplicateCleanupSystem:
    """System to clean up duplicate PDFs"""
    
    def __init__(self, db_path: str, docs_dir: Path):
        self.db_path = db_path
        self.docs_dir = Path(docs_dir)
        self.detector = PDFDuplicateDetector(db_path, docs_dir)
        
    def cleanup_duplicates(self, dry_run: bool = False) -> Dict[str, int]:
        """Clean up duplicate PDFs from database and filesystem"""
        stats = {
            'groups_found': 0,
            'files_removed': 0,
            'space_saved_bytes': 0,
            'errors': 0
        }
        
        print("🧹 Starting duplicate cleanup...")
        
        # Find all duplicate groups
        duplicate_groups = self.detector.find_duplicates_in_database()
        stats['groups_found'] = len(duplicate_groups)
        
        if not duplicate_groups:
            print("✅ No duplicates found!")
            return stats
        
        print(f"🔍 Found {len(duplicate_groups)} duplicate groups")
        
        for group in duplicate_groups:
            try:
                keep_doc = group['keep']
                remove_docs = group['remove']
                
                print(f"\n📁 Processing group with hash {group['hash'][:8]}...")
                print(f"  ✅ Keeping: {keep_doc['original_name']} (ID: {keep_doc['id'][:8]}...)")
                print(f"     Upload: {keep_doc['upload_date']} | Last Opened: {keep_doc['last_opened']}")
                
                # Update the kept document to preserve best metadata
                self._update_kept_document(keep_doc, remove_docs, dry_run)
                
                # Remove duplicate documents
                for doc in remove_docs:
                    print(f"  🗑️ Removing: {doc['original_name']} (ID: {doc['id'][:8]}...)")
                    
                    if not dry_run:
                        # Remove from database
                        success = self._remove_document_from_db(doc['id'])
                        if success:
                            stats['files_removed'] += 1
                            stats['space_saved_bytes'] += doc['file_size'] or 0
                            
                            # Remove physical file
                            self._remove_physical_file(doc['file_path'])
                        else:
                            stats['errors'] += 1
                    else:
                        print(f"    [DRY RUN] Would remove document and file")
                        stats['files_removed'] += 1
                        stats['space_saved_bytes'] += doc['file_size'] or 0
                        
            except Exception as e:
                logger.error(f"Error processing duplicate group: {e}")
                stats['errors'] += 1
        
        # Print summary
        print(f"\n📊 Cleanup Summary:")
        print(f"   - Duplicate groups processed: {stats['groups_found']}")
        print(f"   - Files removed: {stats['files_removed']}")
        print(f"   - Space saved: {stats['space_saved_bytes'] / 1024 / 1024:.2f} MB")
        print(f"   - Errors: {stats['errors']}")
        
        if dry_run:
            print(f"\n⚠️ This was a DRY RUN - no files were actually removed")
        
        return stats
    
    def _update_kept_document(self, keep_doc: Dict, remove_docs: List[Dict], dry_run: bool):
        """Update the kept document with best metadata from all duplicates"""
        try:
            # Find the earliest upload date
            earliest_upload = keep_doc['upload_date']
            for doc in remove_docs:
                if doc['upload_date'] < earliest_upload:
                    earliest_upload = doc['upload_date']
            
            # Find the latest access date
            latest_access = keep_doc['last_opened']
            for doc in remove_docs:
                if doc['last_opened'] and (not latest_access or doc['last_opened'] > latest_access):
                    latest_access = doc['last_opened']
            
            # Update the kept document if needed
            if (earliest_upload != keep_doc['upload_date'] or 
                latest_access != keep_doc['last_opened']):
                
                if not dry_run:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        UPDATE documents 
                        SET upload_date = ?, last_opened = ?, updated_at = ?
                        WHERE id = ?
                    ''', (earliest_upload, latest_access, datetime.now(), keep_doc['id']))
                    
                    conn.commit()
                    conn.close()
                    
                    print(f"    📝 Updated metadata: upload={earliest_upload}, last_opened={latest_access}")
                else:
                    print(f"    [DRY RUN] Would update metadata")
                    
        except Exception as e:
            logger.error(f"Error updating kept document {keep_doc['id']}: {e}")
    
    def _remove_document_from_db(self, document_id: str) -> bool:
        """Remove document from database"""
        try:
            return db.delete_document(document_id, soft_delete=False)  # Hard delete for duplicates
        except Exception as e:
            logger.error(f"Error removing document {document_id} from database: {e}")
            return False
    
    def _remove_physical_file(self, file_path: Path):
        """Remove physical file from filesystem"""
        try:
            if file_path.exists():
                file_path.unlink()
                print(f"    🗑️ Removed file: {file_path.name}")
            else:
                print(f"    ⚠️ File not found: {file_path}")
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}")
    
    def check_for_duplicate_before_upload(self, file_path: Path, original_name: str) -> Optional[Dict]:
        """Check if a file is a duplicate before uploading"""
        try:
            # Calculate hash of new file
            new_file_hash = self.detector.calculate_file_hash(file_path)
            if not new_file_hash:
                return None
            
            # Check database for existing file with same hash
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, original_name, filename, upload_date, last_opened
                FROM documents 
                WHERE file_hash = ? AND status != "deleted"
                LIMIT 1
            ''', (new_file_hash,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'original_name': result[1],
                    'filename': result[2],
                    'upload_date': result[3],
                    'last_opened': result[4],
                    'is_duplicate': True
                }
            
            # Also check by normalized filename
            normalized_name = self.detector.normalize_filename(original_name)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, original_name, filename, upload_date, last_opened, file_hash
                FROM documents 
                WHERE status != "deleted"
            ''')
            
            for row in cursor.fetchall():
                existing_normalized = self.detector.normalize_filename(row[1] or "")
                if existing_normalized == normalized_name and existing_normalized:
                    # Found potential duplicate by name, verify with file comparison
                    existing_file_path = self.docs_dir / row[2]
                    if existing_file_path.exists():
                        comparison = self.detector.are_pdfs_identical(file_path, existing_file_path)
                        if self.detector.is_duplicate(comparison):
                            conn.close()
                            return {
                                'id': row[0],
                                'original_name': row[1],
                                'filename': row[2],
                                'upload_date': row[3],
                                'last_opened': row[4],
                                'is_duplicate': True
                            }
            
            conn.close()
            return None
            
        except Exception as e:
            logger.error(f"Error checking for duplicate: {e}")
            return None
