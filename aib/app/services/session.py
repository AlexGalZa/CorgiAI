"""
Session & message CRUD — with in-memory fallback when PostgreSQL is unavailable.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from app.database import query, query_one, is_db_available

# ═══════════════════════════════════════════════════════════════════════
# In-memory store (used when PostgreSQL is not available)
# ═══════════════════════════════════════════════════════════════════════
_sessions: dict[str, dict] = {}
_messages: dict[str, list[dict]] = {}  # session_id -> list of messages
_message_counter = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_msg_id() -> int:
    global _message_counter
    _message_counter += 1
    return _message_counter


# ═══════════════════════════════════════════════════════════════════════
# Sessions
# ═══════════════════════════════════════════════════════════════════════

def create_session() -> dict:
    """Create a new active session and return it."""
    if is_db_available():
        return query_one(
            "INSERT INTO sessions (status) VALUES ('active') RETURNING *"
        )

    # In-memory fallback
    sid = str(uuid.uuid4())
    session = {
        "id": sid,
        "status": "active",
        "created_at": _now(),
        "updated_at": _now(),
        "completed_at": None,
    }
    _sessions[sid] = session
    _messages[sid] = []
    return session


def get_session(session_id: str) -> dict | None:
    """Get a session by UUID."""
    if is_db_available():
        return query_one("SELECT * FROM sessions WHERE id = %s", (session_id,))

    return _sessions.get(session_id)


def get_session_with_messages(session_id: str) -> dict | None:
    """Get a session together with its ordered messages."""
    if is_db_available():
        session = get_session(session_id)
        if session is None:
            return None
        messages = query(
            """SELECT id, role, content, attachments, created_at
               FROM messages
               WHERE session_id = %s
               ORDER BY created_at ASC""",
            (session_id,),
        )
        session["messages"] = messages
        return session

    # In-memory fallback
    session = _sessions.get(session_id)
    if session is None:
        return None
    result = dict(session)
    result["messages"] = list(_messages.get(session_id, []))
    return result


def list_sessions(status: str | None = None) -> list[dict]:
    """List sessions, optionally filtered by status."""
    if is_db_available():
        if status:
            return query(
                "SELECT * FROM sessions WHERE status = %s ORDER BY created_at DESC",
                (status,),
            )
        return query("SELECT * FROM sessions ORDER BY created_at DESC")

    # In-memory fallback
    sessions = list(_sessions.values())
    if status:
        sessions = [s for s in sessions if s["status"] == status]
    sessions.sort(key=lambda s: s["created_at"], reverse=True)
    return sessions


def update_session_status(session_id: str, status: str) -> dict | None:
    """Update a session's status (active → completed / abandoned)."""
    if is_db_available():
        completed_at = "NOW()" if status == "completed" else "NULL"
        return query_one(
            f"""UPDATE sessions
                SET status = %s, updated_at = NOW(), completed_at = {completed_at}
                WHERE id = %s
                RETURNING *""",
            (status, session_id),
        )

    # In-memory fallback
    session = _sessions.get(session_id)
    if session is None:
        return None
    session["status"] = status
    session["updated_at"] = _now()
    if status == "completed":
        session["completed_at"] = _now()
    return session


# ═══════════════════════════════════════════════════════════════════════
# Messages
# ═══════════════════════════════════════════════════════════════════════

def add_message(
    session_id: str,
    role: str,
    content: str,
    attachments: list | None = None,
) -> dict:
    """Insert a message and bump the session's updated_at timestamp."""
    attachments = attachments or []

    if is_db_available():
        msg = query_one(
            """INSERT INTO messages (session_id, role, content, attachments)
               VALUES (%s, %s, %s, %s)
               RETURNING *""",
            (session_id, role, content, json.dumps(attachments)),
        )
        query("UPDATE sessions SET updated_at = NOW() WHERE id = %s", (session_id,))
        return msg

    # In-memory fallback
    msg = {
        "id": _next_msg_id(),
        "session_id": session_id,
        "role": role,
        "content": content,
        "attachments": attachments,
        "created_at": _now(),
    }
    if session_id not in _messages:
        _messages[session_id] = []
    _messages[session_id].append(msg)

    # Bump session updated_at
    if session_id in _sessions:
        _sessions[session_id]["updated_at"] = _now()

    return msg


def get_messages(session_id: str) -> list[dict]:
    """Return all messages for a session, ordered chronologically."""
    if is_db_available():
        return query(
            """SELECT id, role, content, attachments, created_at
               FROM messages
               WHERE session_id = %s
               ORDER BY created_at ASC""",
            (session_id,),
        )

    # In-memory fallback
    return list(_messages.get(session_id, []))
