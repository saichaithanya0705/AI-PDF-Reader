"""SQLite chat history manager."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class ChatHistoryManager:
    """Manages chat conversation history in local SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        backend_dir = Path(__file__).parent.parent
        self.db_path = Path(db_path or backend_dir / "data" / "chat_history.db").resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()
        print(f"✅ Chat history using SQLite: {self.db_path}")

    def _init_sqlite(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    context_type TEXT DEFAULT 'library',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id)")
            conn.commit()

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        context_type: str = "library",
    ) -> str:
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        title = title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (id, user_id, title, context_type, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, title, context_type, now, now),
            )
            conn.commit()

        return session_id

    async def save_message(
        self,
        user_id: str,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if session_id == "default":
            existing = await self.get_session(session_id, user_id)
            if not existing:
                session_id = await self.create_session(user_id, "Default Conversation")

        message_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    json.dumps(metadata) if metadata is not None else None,
                    now,
                ),
            )
            conn.execute(
                "UPDATE chat_sessions SET updated_at = ? WHERE id = ? AND user_id = ?",
                (now, session_id, user_id),
            )
            conn.commit()

    async def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT id, session_id, role, content, metadata, created_at
            FROM chat_messages
            WHERE session_id = ?
            ORDER BY created_at ASC
        """
        params: List[Any] = [session_id]
        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        messages = []
        for row in rows:
            item = dict(row)
            item["metadata"] = json.loads(item["metadata"]) if item.get("metadata") else None
            messages.append(item)
        return messages

    async def list_user_sessions(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, user_id, title, context_type, created_at, updated_at
                FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    async def get_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        query = """
            SELECT id, user_id, title, context_type, created_at, updated_at
            FROM chat_sessions
            WHERE id = ?
        """
        params: List[Any] = [session_id]
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(query, params).fetchone()
        return dict(row) if row else None

    async def delete_session(
        self,
        session_id: str,
        user_id: str,
    ) -> bool:
        session = await self.get_session(session_id, user_id)
        if not session:
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM chat_messages WHERE session_id = ?", (session_id,))
            cursor = conn.execute(
                "DELETE FROM chat_sessions WHERE id = ? AND user_id = ?",
                (session_id, user_id),
            )
            conn.commit()
        return cursor.rowcount > 0


_chat_history_manager: Optional[ChatHistoryManager] = None


def get_chat_history_manager() -> ChatHistoryManager:
    """Get or create the global chat history manager instance."""
    global _chat_history_manager
    if _chat_history_manager is None:
        _chat_history_manager = ChatHistoryManager()
    return _chat_history_manager
