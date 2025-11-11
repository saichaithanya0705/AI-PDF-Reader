"""
Supabase Database Module for PDF Document Management
Replaces SQLite with Supabase for user-specific PDF storage
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json
from supabase import create_client, Client
import logging

logger = logging.getLogger(__name__)

@dataclass
class Document:
    """Document model representing a PDF file in the system"""
    id: str
    user_id: str
    filename: str
    original_name: str
    upload_date: datetime
    file_size: int
    file_path: str
    status: str = 'uploaded'
    persona: Optional[str] = None
    job_role: Optional[str] = None
    processing_status: str = 'pending'
    validation_result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_uploaded: Optional[datetime] = None
    last_opened: Optional[datetime] = None
    last_accessed: Optional[datetime] = None
    tags: Optional[List[str]] = None
    file_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.upload_date:
            data['upload_date'] = self.upload_date.isoformat()
        if self.last_uploaded:
            data['last_uploaded'] = self.last_uploaded.isoformat()
        if self.last_opened:
            data['last_opened'] = self.last_opened.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary"""
        # Convert ISO strings back to datetime objects
        if 'upload_date' in data and isinstance(data['upload_date'], str):
            data['upload_date'] = datetime.fromisoformat(data['upload_date'].replace('Z', '+00:00'))
        if 'last_uploaded' in data and data['last_uploaded'] and isinstance(data['last_uploaded'], str):
            data['last_uploaded'] = datetime.fromisoformat(data['last_uploaded'].replace('Z', '+00:00'))
        if 'last_opened' in data and data['last_opened'] and isinstance(data['last_opened'], str):
            data['last_opened'] = datetime.fromisoformat(data['last_opened'].replace('Z', '+00:00'))
        if 'last_accessed' in data and data['last_accessed'] and isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'].replace('Z', '+00:00'))
        if 'created_at' in data:
            del data['created_at']
        if 'updated_at' in data:
            del data['updated_at']
        return cls(**data)


class SupabaseDatabase:
    """Database operations for document management using Supabase"""
    
    def __init__(self, supabase_url: str = None, supabase_key: str = None):
        """Initialize Supabase client"""
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
        
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info(f"✅ Supabase database initialized: {self.supabase_url}")
        
        # Ensure docs directory exists for file storage
        backend_dir = Path(__file__).parent.parent
        self.docs_dir = backend_dir / "data" / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Docs directory at: {self.docs_dir}")
    
    def create_document(self,
                       user_id: str,
                       filename: str,
                       original_name: str,
                       file_size: int,
                       file_path: str,
                       persona: Optional[str] = None,
                       job_role: Optional[str] = None,
                       validation_result: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       file_hash: Optional[str] = None) -> Document:
        """Create a new document record"""
        
        now = datetime.now()
        document_data = {
            'user_id': user_id,
            'filename': filename,
            'original_name': original_name,
            'upload_date': now.isoformat(),
            'file_size': file_size,
            'file_path': file_path,
            'persona': persona,
            'job_role': job_role,
            'validation_result': validation_result,
            'metadata': metadata,
            'last_uploaded': now.isoformat(),
            'file_hash': file_hash,
            'status': 'uploaded',
            'processing_status': 'pending'
        }
        
        result = self.client.table('documents').insert(document_data).execute()
        
        if result.data:
            return Document.from_dict(result.data[0])
        else:
            raise Exception("Failed to create document")
    
    def get_all_documents(self, user_id: str, limit: Optional[int] = None, offset: int = 0) -> List[Document]:
        """Get all documents for a specific user with optional pagination"""
        query = self.client.table('documents').select('*').eq('user_id', user_id).neq('status', 'deleted')
        
        # Sort by last_opened if available, otherwise by upload_date
        query = query.order('last_opened', desc=True, nullsfirst=False).order('upload_date', desc=True)
        
        if limit:
            query = query.limit(limit).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        documents = []
        for row in result.data:
            documents.append(Document.from_dict(row))
        
        return documents
    
    def get_document_by_id(self, document_id: str, user_id: str) -> Optional[Document]:
        """Get a specific document by ID for a user"""
        result = self.client.table('documents').select('*').eq('id', document_id).eq('user_id', user_id).execute()
        
        if result.data:
            return Document.from_dict(result.data[0])
        return None
    
    def update_document(self, document_id: str, user_id: str, **updates) -> bool:
        """Update document fields"""
        if not updates:
            return False
        
        # Add updated_at timestamp
        updates['updated_at'] = datetime.now().isoformat()
        
        result = self.client.table('documents').update(updates).eq('id', document_id).eq('user_id', user_id).execute()
        
        return len(result.data) > 0
    
    def delete_document(self, document_id: str, user_id: str, soft_delete: bool = True) -> bool:
        """Delete a document (soft delete by default)"""
        if soft_delete:
            return self.update_document(document_id, user_id, status='deleted')
        else:
            result = self.client.table('documents').delete().eq('id', document_id).eq('user_id', user_id).execute()
            return len(result.data) > 0
    
    def update_last_opened(self, document_id: str, user_id: str) -> bool:
        """Update the last_opened timestamp for a document"""
        return self.update_document(document_id, user_id, last_opened=datetime.now().isoformat())
    
    def update_last_uploaded(self, document_id: str, user_id: str) -> bool:
        """Update last uploaded timestamp"""
        return self.update_document(document_id, user_id, last_uploaded=datetime.now().isoformat())
    
    def find_duplicate_by_hash(self, file_hash: str, user_id: str) -> Optional[Document]:
        """Find document with matching hash for a specific user"""
        result = self.client.table('documents').select('*').eq('file_hash', file_hash).eq('user_id', user_id).neq('status', 'deleted').execute()
        
        if result.data:
            return Document.from_dict(result.data[0])
        return None
    
    def get_document_stats(self, user_id: str) -> Dict[str, Any]:
        """Get database statistics for a user"""
        result = self.client.table('documents').select('*', count='exact').eq('user_id', user_id).neq('status', 'deleted').execute()
        
        total_documents = result.count or 0
        total_size = sum(doc.get('file_size', 0) for doc in result.data)
        uploaded = sum(1 for doc in result.data if doc.get('status') == 'uploaded')
        processed = sum(1 for doc in result.data if doc.get('processing_status') == 'completed')
        opened = sum(1 for doc in result.data if doc.get('last_opened'))
        
        return {
            'total_documents': total_documents,
            'uploaded_documents': uploaded,
            'processed_documents': processed,
            'opened_documents': opened,
            'total_size_bytes': total_size
        }
    
    def store_chunk(
        self,
        user_id: str,
        document_id: str,
        chunk_text: str,
        chunk_index: int,
        page_number: int,
        embedding: Optional[List[float]] = None,
        char_count: Optional[int] = None,
        word_count: Optional[int] = None
    ) -> str:
        """Store a document chunk in the database"""
        chunk_data = {
            'user_id': user_id,
            'document_id': document_id,
            'chunk_text': chunk_text,
            'chunk_index': chunk_index,
            'page_number': page_number,
            'embedding': embedding,
            'char_count': char_count,
            'word_count': word_count
        }
        
        result = self.client.table('document_chunks').insert(chunk_data).execute()
        
        if result.data:
            return result.data[0]['id']
        else:
            raise Exception("Failed to store chunk")
    
    def get_chunks_by_document(self, document_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        result = self.client.table('document_chunks').select('*').eq('document_id', document_id).eq('user_id', user_id).order('chunk_index').execute()
        
        return result.data
    
    def delete_chunks_by_document(self, document_id: str, user_id: str) -> int:
        """Delete all chunks for a document"""
        result = self.client.table('document_chunks').delete().eq('document_id', document_id).eq('user_id', user_id).execute()
        return len(result.data)
    
    def get_chunk_count(self, user_id: str, document_id: Optional[str] = None) -> int:
        """Get total chunk count for a user, optionally filtered by document"""
        query = self.client.table('document_chunks').select('*', count='exact').eq('user_id', user_id)
        
        if document_id:
            query = query.eq('document_id', document_id)
        
        result = query.execute()
        return result.count or 0


# Global database instance - will be initialized in main.py
supabase_db: Optional[SupabaseDatabase] = None


def get_supabase_db() -> SupabaseDatabase:
    """Get the global Supabase database instance"""
    global supabase_db
    if supabase_db is None:
        supabase_db = SupabaseDatabase()
    return supabase_db
