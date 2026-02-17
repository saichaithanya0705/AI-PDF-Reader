"""
Chat History Manager Module

Handles persistence of chat conversations to database.
Supports both Supabase (production) and SQLite (local) storage.
"""

import os
import json
# sqlite3 import removed
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import uuid

# Check if Supabase is available
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase not available, using SQLite for chat history")


class ChatHistoryManager:
    """Manages chat conversation history with database persistence"""
    
    def __init__(self):
        """Initialize chat history manager with separate storage backend"""
        self.use_supabase = True
        
        if SUPABASE_AVAILABLE:
            self._init_supabase()
        else:
            print("❌ Supabase client not installed or available.")
            self.use_supabase = False
    
    def _init_supabase(self):
        """Initialize Supabase client"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Supabase credentials not found.")
            self.use_supabase = False
            return
        
        try:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            self._create_supabase_tables()
            print("✅ Chat history using Supabase")
        except Exception as e:
            print(f"❌ Supabase initialization failed: {e}")
            self.use_supabase = False
    
    def _create_supabase_tables(self):
        """Create Supabase tables if they don't exist"""
        # Tables are created via Supabase migrations
        # This is a placeholder for table verification
        pass
    
    # SQLite methods removed
    
    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        context_type: str = "library"
    ) -> str:
        """
        Create a new chat session
        
        Args:
            user_id: User identifier
            title: Optional session title
            context_type: 'library' or 'pdf_viewer'
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if self.use_supabase:
            self.supabase.table("chat_sessions").insert({
                "id": session_id,
                "user_id": user_id,
                "title": title,
                "context_type": context_type,
                "created_at": now,
                "updated_at": now
            }).execute()
        
        return session_id
    
    async def save_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Save a chat message to the database
        
        Args:
            user_id: User identifier
            session_id: Chat session ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (related_documents, context, etc.)
        """
        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Create session if it doesn't exist (for backward compatibility)
        if session_id == "default":
            # Check if default session exists for this user
            existing = await self.get_session(session_id, user_id)
            if not existing:
                session_id = await self.create_session(user_id, "Default Conversation")
        
        if self.use_supabase:
            self.supabase.table("chat_messages").insert({
                "id": message_id,
                "session_id": session_id,
                "role": role,
                "content": content,
                "metadata": metadata,
                "created_at": now
            }).execute()
            
            # Update session timestamp
            self.supabase.table("chat_sessions").update({
                "updated_at": now
            }).eq("id", session_id).execute()
    
    async def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve conversation history for a session
        
        Args:
            session_id: Chat session ID
            limit: Optional limit on number of messages
            
        Returns:
            List of messages with role, content, metadata, and timestamp
        """
        if self.use_supabase:
            query = self.supabase.table("chat_messages").select("*").eq("session_id", session_id).order("created_at", desc=False)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            messages = result.data
            
            # Parse metadata from JSON
            for msg in messages:
                if msg.get("metadata"):
                    msg["metadata"] = json.loads(msg["metadata"]) if isinstance(msg["metadata"], str) else msg["metadata"]
            
            return messages
        
        return []
    
    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all chat sessions for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of sessions to return
            
        Returns:
            List of session dictionaries
        """
        if self.use_supabase:
            result = self.supabase.table("chat_sessions").select("*").eq("user_id", user_id).order("updated_at", desc=True).limit(limit).execute()
            return result.data
        return []
    
    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific session by ID
        
        Args:
            session_id: Chat session ID
            user_id: Optional user ID for verification
            
        Returns:
            Session dictionary or None
        """
        if self.use_supabase:
            query = self.supabase.table("chat_sessions").select("*").eq("id", session_id)
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            return result.data[0] if result.data else None
        
        return None
    
    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a chat session and all its messages
        
        Args:
            session_id: Chat session ID
            user_id: User ID (for verification)
            
        Returns:
            True if deleted, False if not found or unauthorized
        """
        # Verify ownership
        session = await self.get_session(session_id, user_id)
        if not session:
            return False
        
        if self.use_supabase:
            # Delete messages first (cascade should handle this, but being explicit)
            self.supabase.table("chat_messages").delete().eq("session_id", session_id).execute()
            self.supabase.table("chat_sessions").delete().eq("id", session_id).execute()
        
        return True
        
        return True


# Global instance
_chat_history_manager = None

def get_chat_history_manager() -> ChatHistoryManager:
    """Get or create the global chat history manager instance"""
    global _chat_history_manager
    if _chat_history_manager is None:
        _chat_history_manager = ChatHistoryManager()
    return _chat_history_manager
