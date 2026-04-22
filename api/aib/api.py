import secrets
from uuid import UUID
from ninja import Router, Schema
from ninja.errors import HttpError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from django.db import transaction

from aib.models import AibSession, AibMessage
from aib.service import AibService


router = Router(tags=["aib"])


def _resolve_session(session_id: UUID, request: HttpRequest) -> AibSession:
    """Return session if the request has the matching token, else raise 403."""
    session = get_object_or_404(AibSession, id=session_id)
    token = request.headers.get("X-AIB-Token", "")
    if not secrets.compare_digest(token, session.session_token):
        raise HttpError(403, "Invalid session token")
    return session


def get_user_from_request(request: HttpRequest):
    if request.user and request.user.is_authenticated:
        return request.user
    return None


# --- Schemas ---

class CreateSessionOut(Schema):
    session_id: UUID
    session_token: str


class MessageOut(Schema):
    id: UUID
    role: str
    content: str
    extracted_fields: dict
    created_at: str


class SessionOut(Schema):
    session_id: UUID
    messages: list[MessageOut]


class SendMessageIn(Schema):
    content: str
    step: str = "get-started"


class SendMessageOut(Schema):
    message: str
    extracted_fields: dict


class ClaimIn(Schema):
    session_token: str


class ClaimOut(Schema):
    ok: bool


# --- Endpoints ---

@router.post("/sessions/", response={201: CreateSessionOut}, auth=None)
def create_session(request: HttpRequest):
    session = AibSession.objects.create()
    return 201, {"session_id": session.id, "session_token": session.session_token}


@router.get("/sessions/{session_id}/", response=SessionOut, auth=None)
def get_session(request: HttpRequest, session_id: UUID):
    session = _resolve_session(session_id, request)
    messages_qs = session.messages.values("id", "role", "content", "extracted_fields", "created_at")
    messages = [
        {**m, "id": str(m["id"]), "created_at": m["created_at"].isoformat()}
        for m in messages_qs
    ]
    return {"session_id": session.id, "messages": messages}


@router.post("/sessions/{session_id}/messages/", response=SendMessageOut, auth=None)
@transaction.atomic
def send_message(request: HttpRequest, session_id: UUID, payload: SendMessageIn):
    session = _resolve_session(session_id, request)

    AibMessage.objects.create(
        session=session,
        role="user",
        content=payload.content,
    )

    history = list(session.messages.values("role", "content"))
    svc = AibService()
    reply, extracted = svc.chat(history, step=payload.step)

    non_null = {k: v for k, v in extracted.items() if v is not None}
    AibMessage.objects.create(
        session=session,
        role="assistant",
        content=reply,
        extracted_fields=non_null,
    )

    return {"message": reply, "extracted_fields": non_null}


@router.post("/sessions/{session_id}/claim/", response=ClaimOut, auth=None)
def claim_session(request: HttpRequest, session_id: UUID, payload: ClaimIn):
    session = get_object_or_404(AibSession, id=session_id)
    if not secrets.compare_digest(payload.session_token, session.session_token):
        raise HttpError(403, "Invalid session token")
    user = get_user_from_request(request)
    if user:
        session.user = user
        session.save(update_fields=["user", "updated_at"])
    return {"ok": True}
