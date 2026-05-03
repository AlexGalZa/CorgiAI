import secrets
from typing import Optional
from uuid import UUID
from ninja import Router, Schema, UploadedFile, File, Form
from ninja.errors import HttpError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404

from aib.models import AibSession, AibMessage
from aib.service import AibService, SUPPORTED_IMAGE_TYPES, SUPPORTED_DOC_TYPES, MAX_FILE_BYTES
from users.auth import JWTAuth


router = Router(tags=["aib"])

ALLOWED_MIME_TYPES = SUPPORTED_IMAGE_TYPES | SUPPORTED_DOC_TYPES


def _resolve_session(session_id: UUID, request: HttpRequest) -> AibSession:
    """Return session if the request has the matching token, else raise 403."""
    session = get_object_or_404(AibSession, id=session_id)
    token = request.headers.get("X-AIB-Token", "")
    if not secrets.compare_digest(token, session.session_token):
        raise HttpError(403, "Invalid session token")
    return session


# --- Schemas ---

class CreateSessionOut(Schema):
    session_id: UUID
    session_token: str


class MessageOut(Schema):
    id: UUID
    role: str
    content: str
    file_name: Optional[str]
    extracted_fields: dict
    created_at: str


class SessionOut(Schema):
    session_id: UUID
    messages: list[MessageOut]


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
    messages_qs = session.messages.values("id", "role", "content", "file_name", "extracted_fields", "created_at")
    messages = [
        {**m, "id": str(m["id"]), "created_at": m["created_at"].isoformat()}
        for m in messages_qs
    ]
    return {"session_id": session.id, "messages": messages}


@router.post("/sessions/{session_id}/messages/", response=SendMessageOut, auth=None)
def send_message(
    request: HttpRequest,
    session_id: UUID,
    content: str = Form(...),
    step: str = Form("get-started"),
    file: Optional[UploadedFile] = File(None),
):
    session = _resolve_session(session_id, request)

    file_data = None
    file_name = None
    if file is not None:
        media_type = file.content_type or ""
        if media_type not in ALLOWED_MIME_TYPES:
            raise HttpError(400, f"Unsupported file type: {media_type}. Allowed: PDF, JPEG, PNG, GIF, WebP.")
        raw = file.read()
        if len(raw) > MAX_FILE_BYTES:
            raise HttpError(400, "File exceeds 10 MB limit.")
        file_name = file.name
        file_data = {"media_type": media_type, "data": raw, "file_name": file_name}

    stored_content = f"[Attached: {file_name}]\n\n{content}" if file_name else content

    AibMessage.objects.create(
        session=session,
        role="user",
        content=stored_content,
        file_name=file_name,
    )

    history = list(session.messages.values("role", "content"))
    svc = AibService()
    reply, extracted = svc.chat(history, step=step, file_data=file_data)

    non_null = {k: v for k, v in extracted.items() if v is not None}
    AibMessage.objects.create(
        session=session,
        role="assistant",
        content=reply,
        extracted_fields=non_null,
    )

    return {"message": reply, "extracted_fields": non_null}


@router.post("/sessions/{session_id}/claim/", response=ClaimOut, auth=JWTAuth())
def claim_session(request: HttpRequest, session_id: UUID, payload: ClaimIn):
    session = get_object_or_404(AibSession, id=session_id)
    if not secrets.compare_digest(payload.session_token, session.session_token):
        raise HttpError(403, "Invalid session token")
    user = request.auth  # populated by JWTAuth
    if user and hasattr(user, "pk"):
        session.user = user
        session.save(update_fields=["user", "updated_at"])
    return {"ok": True}
