"""
Intake REST endpoints — mirrors server/src/routes/intakes.js
"""

from fastapi import APIRouter, HTTPException

from app.services import extraction as extraction_svc
from app.services import session as session_svc

router = APIRouter(prefix="/api/intakes", tags=["intakes"])


@router.get("")
async def list_intakes():
    """List all completed intakes."""
    return extraction_svc.list_intakes()


@router.get("/{session_id}")
async def get_intake(session_id: str):
    """Get extracted intake data for a specific session."""
    intake = extraction_svc.get_intake(session_id)
    if not intake:
        raise HTTPException(status_code=404, detail="Intake not found")
    return intake


@router.get("/{session_id}/transcript")
async def get_transcript(session_id: str):
    """Get the full conversation transcript for a session."""
    session = session_svc.get_session_with_messages(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    transcript = [
        {
            "role": m["role"],
            "content": m["content"],
            "timestamp": m.get("created_at"),
        }
        for m in session.get("messages", [])
    ]

    return {
        "session_id": session["id"],
        "status": session["status"],
        "created_at": session.get("created_at"),
        "completed_at": session.get("completed_at"),
        "transcript": transcript,
    }
