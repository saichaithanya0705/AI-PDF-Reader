import asyncio
import sqlite3

from backend.app.chat_history import ChatHistoryManager


def test_sqlite_chat_history_persists_sessions_and_messages(tmp_path):
    manager = ChatHistoryManager(tmp_path / "chat_history.db")

    session_id = asyncio.run(
        manager.create_session(
            user_id="user-1",
            title="Test chat",
            context_type="library",
        )
    )
    asyncio.run(
        manager.save_message(
            user_id="user-1",
            session_id=session_id,
            role="user",
            content="hello",
            metadata={"source": "test"},
        )
    )

    sessions = asyncio.run(manager.list_user_sessions("user-1"))
    history = asyncio.run(manager.get_session_history(session_id))

    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"] == "Test chat"
    assert history[0]["content"] == "hello"
    assert history[0]["metadata"] == {"source": "test"}

    with sqlite3.connect(tmp_path / "chat_history.db") as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"chat_sessions", "chat_messages"}.issubset(tables)
