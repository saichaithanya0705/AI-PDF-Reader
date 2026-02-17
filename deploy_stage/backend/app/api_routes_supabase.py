"""
API routes for document management with Supabase authentication
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path as FilePath
from datetime import datetime
import json
import shutil
import logging

from .auth_middleware import get_current_user, get_optional_user
from .supabase_database import get_supabase_db, Document

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents", response_model=Dict[str, Any])
async def get_all_documents(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip"),
    search: Optional[str] = Query(None, description="Search in document names and metadata"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all documents for the authenticated user with optional filtering and pagination
    """
    try:
        user_id = current_user["sub"]
        logger.info(f"📚 API: get_all_documents called for user {user_id}")
        
        db = get_supabase_db()
        documents = db.get_all_documents(user_id=user_id, limit=limit, offset=offset)
        
        logger.info(f"📚 API: Found {len(documents)} documents for user")
        
        # Convert documents to dictionaries for JSON response
        document_dicts = []
        for doc in documents:
            doc_dict = doc.to_dict()
            # Add file URL for frontend
            doc_dict['url'] = f"/api/files/{doc.filename}"
            document_dicts.append(doc_dict)
        
        stats = db.get_document_stats(user_id)
        logger.info(f"📊 API: Database stats: {stats}")
        
        response_data = {
            "documents": document_dicts,
            "count": len(document_dicts),
            "total_count": stats['total_documents'],
            "stats": stats
        }
        
        logger.info(f"📤 API: Returning {len(document_dicts)} documents to frontend")
        return response_data
        
    except Exception as e:
        logger.error(f"❌ Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@router.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: str = Path(..., description="Document ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific document by ID for the authenticated user
    """
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        document = db.get_document_by_id(document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_dict = document.to_dict()
        doc_dict['url'] = f"/api/files/{document.filename}"
        
        # Update last opened time
        db.update_last_opened(document_id, user_id)
        
        return {
            "document": doc_dict,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str = Path(..., description="Document ID"),
    permanent: bool = Query(False, description="Permanently delete (default: soft delete)"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a document (soft delete by default) for the authenticated user
    """
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        # Get document to verify ownership and get file path
        document = db.get_document_by_id(document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from database
        success = db.delete_document(document_id, user_id, soft_delete=not permanent)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # If permanent delete, also remove the file
        if permanent:
            try:
                file_path = FilePath(document.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"🗑️ Deleted file: {file_path}")
            except Exception as e:
                logger.error(f"⚠️ Failed to delete file: {e}")
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "permanent": permanent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    """
    Get statistics for the authenticated user's documents
    """
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        stats = db.get_document_stats(user_id)
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


@router.post("/documents/{document_id}/update-metadata")
async def update_document_metadata(
    document_id: str = Path(..., description="Document ID"),
    metadata: Dict[str, Any] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Update document metadata for the authenticated user
    """
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        # Verify document exists and belongs to user
        document = db.get_document_by_id(document_id, user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update metadata
        success = db.update_document(document_id, user_id, metadata=metadata)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update document")
        
        return {
            "success": True,
            "message": "Document metadata updated successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating document metadata: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update metadata: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint (no authentication required)
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }
