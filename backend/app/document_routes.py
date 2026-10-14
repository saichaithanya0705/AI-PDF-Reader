"""Document and chat API routes for authenticated users."""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
import json
import shutil
import logging

from .auth_middleware import get_current_user, get_optional_user
from .database import Document
from .document_storage import get_document_storage
from .persistence import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["documents"])

ChatContextType = Literal["library", "pdf_viewer"]


class ChatSessionPayload(BaseModel):
    id: str
    title: str
    context_type: ChatContextType
    created_at: str
    updated_at: str


class ChatMessagePayload(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str


class CreateChatSessionResponse(BaseModel):
    status: str
    session_id: str
    message: str


class ListChatSessionsResponse(BaseModel):
    status: str
    sessions: List[ChatSessionPayload]
    count: int


class GetChatSessionResponse(BaseModel):
    status: str
    session: ChatSessionPayload
    messages: List[ChatMessagePayload]
    count: int


class DeleteChatSessionResponse(BaseModel):
    status: str
    message: str


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
        print(f"DEBUG: get_all_documents user_id: {user_id}")
        logger.info(f"📚 API: get_all_documents called for user {user_id}")
        
        documents = db.get_all_documents(limit=limit, offset=offset, client_id=user_id)

        if search:
            search_lower = search.lower()
            documents = [
                doc for doc in documents
                if search_lower in (doc.original_name or "").lower()
                or search_lower in (doc.filename or "").lower()
                or search_lower in json.dumps(doc.metadata or {}).lower()
            ]
        
        logger.info(f"📚 API: Found {len(documents)} documents for user")
        
        # Convert documents to dictionaries for JSON response
        document_dicts = []
        for doc in documents:
            doc_dict = doc.to_dict()
            # Add file URL for frontend
            doc_dict['url'] = f"/api/files/{doc.filename}"
            document_dicts.append(doc_dict)
        
        stats = db.get_document_stats(client_id=user_id)
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
        
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_dict = document.to_dict()
        doc_dict['url'] = f"/api/files/{document.filename}"
        
        # Update last opened time
        db.update_last_opened(document_id, client_id=user_id)
        
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
        
        # Get document to verify ownership and get file path
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        try:
            from .vector_store import get_vector_store

            db.delete_chunks_by_document(document_id, client_id=user_id)
            get_vector_store().remove_document(document_id)
        except Exception as e:
            logger.warning("Failed to remove RAG data for %s: %s", document_id, e)
        
        # Delete from database
        success = db.delete_document(document_id, soft_delete=not permanent, client_id=user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # If permanent delete, also remove the file
        if permanent:
            try:
                get_document_storage().delete(document.file_path)
                logger.info("Deleted persisted PDF object for document %s", document_id)
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
        
        stats = db.get_document_stats(client_id=user_id)
        
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
        
        # Verify document exists and belongs to user
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Update metadata
        success = db.update_document(document_id, client_id=user_id, metadata=metadata)
        
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


# ==============================================================================
# Chat History Endpoints (SQLite records, Supabase-authenticated user)
# ==============================================================================

@router.post("/chat/sessions", response_model=CreateChatSessionResponse)
async def create_chat_session_endpoint(
    title: Optional[str] = Query(None, description="Session title"),
    context_type: ChatContextType = Query("library", description="Context type: library or pdf_viewer"),
    current_user: dict = Depends(get_current_user)
):
    """
    Create a new chat session for authenticated user
    """
    try:
        from .chat_history import get_chat_history_manager
        
        user_id = current_user["sub"]
        logger.info(f"💬 Creating chat session for user {user_id}")
        
        chat_mgr = get_chat_history_manager()
        
        session_id = await chat_mgr.create_session(
            user_id=user_id,
            title=title,
            context_type=context_type
        )
        
        return {
            "status": "success",
            "session_id": session_id,
            "message": "Chat session created successfully"
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@router.get("/chat/sessions", response_model=ListChatSessionsResponse)
async def list_chat_sessions_endpoint(
    limit: int = Query(50, ge=1, le=100, description="Maximum sessions to return"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get all chat sessions for authenticated user
    """
    try:
        from .chat_history import get_chat_history_manager
        
        user_id = current_user["sub"]
        logger.info(f"💬 Listing chat sessions for user {user_id}")
        
        chat_mgr = get_chat_history_manager()
        
        sessions = await chat_mgr.list_user_sessions(
            user_id=user_id,
            limit=limit
        )
        
        logger.info(f"💬 Found {len(sessions)} sessions")
        
        return {
            "status": "success",
            "sessions": sessions,
            "count": len(sessions)
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing chat sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@router.get("/chat/sessions/{session_id}", response_model=GetChatSessionResponse)
async def get_chat_session_endpoint(
    session_id: str = Path(..., description="Session ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Get messages for a specific session
    """
    try:
        from .chat_history import get_chat_history_manager
        
        user_id = current_user["sub"]
        chat_mgr = get_chat_history_manager()
        
        # Verify session ownership
        session = await chat_mgr.get_session(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found or not authorized")
        
        # Get messages
        messages = await chat_mgr.get_session_history(session_id)
        
        return {
            "status": "success",
            "session": session,
            "messages": messages,
            "count": len(messages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get session: {str(e)}")


@router.delete("/chat/sessions/{session_id}", response_model=DeleteChatSessionResponse)
async def delete_chat_session_endpoint(
    session_id: str = Path(..., description="Session ID"),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a chat session
    """
    try:
        from .chat_history import get_chat_history_manager
        
        user_id = current_user["sub"]
        chat_mgr = get_chat_history_manager()
        
        success = await chat_mgr.delete_session(session_id, user_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Session not found or not authorized")
        
        return {
            "status": "success",
            "message": "Chat session deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
