"""
Chat History Management
Stores and retrieves chat conversations for users
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import uuid

from .auth_middleware import get_current_user
from .supabase_database import get_supabase_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


class ChatSession(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    messages: List[ChatMessage]
    document_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.post("/sessions")
async def create_chat_session(
    session: ChatSession,
    current_user: dict = Depends(get_current_user)
):
    """Create a new chat session"""
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Generate title from first message if not provided
        title = session.title
        if not title and session.messages:
            first_msg = session.messages[0].content
            title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
        
        session_data = {
            'id': session_id,
            'user_id': user_id,
            'title': title or "New Chat",
            'document_id': session.document_id,
            'messages': [msg.dict() for msg in session.messages],
            'created_at': now,
            'updated_at': now
        }
        
        result = db.client.table('chat_sessions').insert(session_data).execute()
        
        return {
            "success": True,
            "session_id": session_id,
            "session": result.data[0] if result.data else session_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error creating chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")


@router.get("/sessions")
async def get_chat_sessions(
    limit: int = 50,
    offset: int = 0,
    document_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all chat sessions for the authenticated user"""
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        query = db.client.table('chat_sessions').select('*').eq('user_id', user_id)
        
        if document_id:
            query = query.eq('document_id', document_id)
        
        query = query.order('updated_at', desc=True).limit(limit).range(offset, offset + limit - 1)
        
        result = query.execute()
        
        return {
            "success": True,
            "sessions": result.data,
            "count": len(result.data)
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching chat sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat sessions: {str(e)}")


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific chat session"""
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        result = db.client.table('chat_sessions').select('*').eq('id', session_id).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {
            "success": True,
            "session": result.data[0]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error fetching chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch chat session: {str(e)}")


@router.put("/sessions/{session_id}")
async def update_chat_session(
    session_id: str,
    session: ChatSession,
    current_user: dict = Depends(get_current_user)
):
    """Update a chat session (add messages, update title, etc.)"""
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        # Verify session belongs to user
        existing = db.client.table('chat_sessions').select('*').eq('id', session_id).eq('user_id', user_id).execute()
        
        if not existing.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        update_data = {
            'messages': [msg.dict() for msg in session.messages],
            'updated_at': datetime.now().isoformat()
        }
        
        if session.title:
            update_data['title'] = session.title
        
        result = db.client.table('chat_sessions').update(update_data).eq('id', session_id).eq('user_id', user_id).execute()
        
        return {
            "success": True,
            "session": result.data[0] if result.data else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error updating chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update chat session: {str(e)}")


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a chat session"""
    try:
        user_id = current_user["sub"]
        db = get_supabase_db()
        
        result = db.client.table('chat_sessions').delete().eq('id', session_id).eq('user_id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {
            "success": True,
            "message": "Chat session deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error deleting chat session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete chat session: {str(e)}")
