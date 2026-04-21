"""
Session management API endpoints (V3 #56).

GET  /api/v1/auth/sessions      — list active sessions for the current user
DELETE /api/v1/auth/sessions/{id} — revoke a specific session
DELETE /api/v1/auth/sessions    — revoke all sessions (logout everywhere)
"""

import logging
from typing import Any

from django.http import HttpRequest
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from users.auth import JWTAuth

router = Router(tags=["Sessions"])
logger = logging.getLogger(__name__)


def _session_to_dict(session) -> dict:
    return {
        "id": session.id,
        "session_key_prefix": session.session_key[:12] + "…",
        "ip_address": session.ip_address,
        "user_agent": session.user_agent,
        "created_at": session.created_at.isoformat(),
        "last_activity": session.last_activity.isoformat(),
        "is_active": session.is_active,
        "is_expired": session.is_expired,
    }


@router.get("", auth=JWTAuth(), response={200: dict})
def list_sessions(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    List all active (non-revoked) sessions for the authenticated user.

    Returns sessions ordered by most recent activity.
    """
    from users.models import ActiveSession

    sessions = ActiveSession.objects.filter(
        user=request.auth,
        is_active=True,
    ).order_by("-last_activity")

    return 200, {
        "success": True,
        "message": "Sessions retrieved",
        "data": [_session_to_dict(s) for s in sessions],
    }


@router.delete("/{session_id}", auth=JWTAuth(), response={200: dict})
def revoke_session(request: HttpRequest, session_id: int) -> tuple[int, dict[str, Any]]:
    """
    Revoke a specific session by ID.

    Users may only revoke their own sessions.
    """
    from users.models import ActiveSession

    try:
        session = ActiveSession.objects.get(id=session_id, user=request.auth)
    except ActiveSession.DoesNotExist:
        raise HttpError(404, "Session not found")

    if not session.is_active:
        raise HttpError(400, "Session is already revoked")

    session.revoke()
    logger.info("Session %s revoked by user %s", session_id, request.auth.email)

    return 200, {
        "success": True,
        "message": "Session revoked",
        "data": None,
    }


@router.delete("", auth=JWTAuth(), response={200: dict})
def revoke_all_sessions(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """
    Revoke all active sessions for the current user (logout everywhere).
    """
    from users.models import ActiveSession

    ActiveSession.objects.filter(
        user=request.auth,
        is_active=True,
    ).update(is_active=True, revoked_at=timezone.now())

    # Use update() then set is_active=False
    ActiveSession.objects.filter(
        user=request.auth,
        is_active=True,
    ).count()
    ActiveSession.objects.filter(
        user=request.auth,
        is_active=True,
    ).update(is_active=False, revoked_at=timezone.now())

    logger.info("All sessions revoked for user %s", request.auth.email)

    return 200, {
        "success": True,
        "message": "All sessions revoked",
        "data": None,
    }
