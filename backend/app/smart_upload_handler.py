#!/usr/bin/env python3
"""
Smart Upload Handler
Prevents duplicate uploads while preserving original upload dates and updating access times
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime
import logging
try:
    from .duplicate_cleanup_system import DuplicateCleanupSystem
    from .database import db
except ImportError:
    from duplicate_cleanup_system import DuplicateCleanupSystem
    from database import db

logger = logging.getLogger(__name__)

class SmartUploadHandler:
    """Handles PDF uploads with intelligent duplicate detection and prevention"""
    
    def __init__(self, docs_dir: Path, db_path: str):
        self.docs_dir = Path(docs_dir)
        self.db_path = db_path
        self.cleanup_system = DuplicateCleanupSystem(db_path, docs_dir)
        
    def handle_upload(self, file_path: Path, original_name: str, client_id: str = None, 
                     persona: str = None, job: str = None) -> Dict[str, any]:
        """
        Handle PDF upload with duplicate detection
        
        Returns:
            - If new file: {'is_duplicate': False, 'document_id': str, 'message': str}
            - If duplicate: {'is_duplicate': True, 'existing_document': dict, 'message': str}
        """
        
        print(f"📤 Processing upload: {original_name}")
        
        # Check for duplicates before processing
        duplicate_info = self.cleanup_system.check_for_duplicate_before_upload(file_path, original_name)
        
        if duplicate_info:
            # Found duplicate - update last_opened time and return existing document
            print(f"🔍 Duplicate detected: {original_name}")
            print(f"   Existing document: {duplicate_info['original_name']} (ID: {duplicate_info['id'][:8]}...)")
            
            # Update last_opened time to current time (user is "accessing" it by uploading again)
            self._update_last_opened(duplicate_info['id'])
            
            return {
                'is_duplicate': True,
                'existing_document': duplicate_info,
                'message': f"File already exists. Updated access time for existing document.",
                'document_id': duplicate_info['id']
            }
        
        # Not a duplicate - proceed with normal upload
        print(f"✅ New file detected: {original_name}")
        return self._process_new_upload(file_path, original_name, client_id, persona, job)
    
    def _update_last_opened(self, document_id: str):
        """Update the last_opened timestamp for an existing document"""
        try:
            db.update_last_opened(document_id)
            print(f"   📝 Updated last_opened time for document {document_id[:8]}...")
        except Exception as e:
            logger.error(f"Error updating last_opened for {document_id}: {e}")
    
    def _process_new_upload(self, file_path: Path, original_name: str, client_id: str = None,
                           persona: str = None, job: str = None) -> Dict[str, any]:
        """Process a new (non-duplicate) file upload"""
        try:
            # Generate unique filename
            import uuid
            file_id = str(uuid.uuid4())
            file_extension = file_path.suffix
            unique_filename = f"{file_id}_{original_name}"
            
            # Ensure unique filename
            target_path = self.docs_dir / unique_filename
            counter = 1
            while target_path.exists():
                name_without_ext = original_name.rsplit('.', 1)[0]
                unique_filename = f"{file_id}_{name_without_ext}_{counter}{file_extension}"
                target_path = self.docs_dir / unique_filename
                counter += 1
            
            # Copy file to docs directory
            shutil.copy2(file_path, target_path)
            
            # Calculate file hash
            file_hash = self.cleanup_system.detector.calculate_file_hash(target_path)
            
            # Get file size
            file_size = target_path.stat().st_size
            
            # Save to database (create_document generates its own ID)
            document = db.create_document(
                filename=unique_filename,
                original_name=original_name,
                file_size=file_size,
                file_path=str(target_path),
                file_hash=file_hash,
                client_id=client_id,
                persona=persona,
                job_role=job
            )
            
            print(f"   💾 Saved new document: {unique_filename}")
            print(f"   📊 File size: {file_size} bytes | Hash: {file_hash[:8]}...")
            
            return {
                'is_duplicate': False,
                'document_id': document.id,
                'filename': unique_filename,
                'message': f"File uploaded successfully as {unique_filename}",
                'document': document
            }
            
        except Exception as e:
            logger.error(f"Error processing new upload {original_name}: {e}")
            raise
    
    def bulk_cleanup_existing_duplicates(self, dry_run: bool = True) -> Dict[str, int]:
        """Clean up existing duplicates in the database"""
        print("🧹 Starting bulk duplicate cleanup...")
        return self.cleanup_system.cleanup_duplicates(dry_run=dry_run)
    
    def get_duplicate_report(self) -> Dict[str, any]:
        """Generate a report of current duplicates in the system"""
        duplicate_groups = self.cleanup_system.detector.find_duplicates_in_database()
        
        total_duplicates = sum(len(group['remove']) for group in duplicate_groups)
        total_space_wasted = sum(
            sum(doc['file_size'] or 0 for doc in group['remove']) 
            for group in duplicate_groups
        )
        
        return {
            'duplicate_groups': len(duplicate_groups),
            'total_duplicate_files': total_duplicates,
            'space_wasted_bytes': total_space_wasted,
            'space_wasted_mb': total_space_wasted / 1024 / 1024,
            'groups': duplicate_groups
        }


def run_duplicate_cleanup(db_instance, docs_dir: Path, dry_run: bool = False) -> Dict[str, int]:
    """
    Enhanced duplicate cleanup function to replace the existing one
    """
    handler = SmartUploadHandler(docs_dir, db_instance.db_path)
    return handler.bulk_cleanup_existing_duplicates(dry_run=dry_run)
