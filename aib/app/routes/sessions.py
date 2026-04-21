"""
Session REST endpoints — mirrors server/src/routes/sessions.js
"""

from fastapi import APIRouter, HTTPException

from app.services import session as session_svc

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", status_code=201)
async def create_session():
    """Create a new active session."""
    session = session_svc.create_session()
    return session


@router.get("")
async def list_sessions(status: str | None = None):
    """List all sessions, optionally filtered by status."""
    return session_svc.list_sessions(status)


@router.get("/{session_id}")
async def get_session(session_id: str):
    """Get session details with messages."""
    session = session_svc.get_session_with_messages(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
