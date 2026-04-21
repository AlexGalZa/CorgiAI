"""
Chat REST endpoints — mirrors server/src/routes/chat.js

Handles text messages (JSON body) and file uploads (multipart/form-data).
"""

from __future__ import annotations

import os
import traceback

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.services import session as session_svc
from app.services import anthropic_client
from app.services import file_processor
from app.services import extraction as extraction_svc

router = APIRouter(prefix="/api/chat", tags=["chat"])


class TextMessage(BaseModel):
    session_id: str
    content: str
    attachments: list = []


@router.post("/message")
async def send_message(request: Request):
    """
    Send a message (with optional file attachment) and get the AI response.

    Accepts either:
    - JSON body: { session_id, content }
    - Multipart form data: session_id, content, file
    """
    content_type = request.headers.get("content-type", "")

    session_id = None
    content = ""
    file = None
    file_filename = None

    if "multipart/form-data" in content_type:
        # Parse multipart form
        form = await request.form()
        session_id = form.get("session_id")
        content = form.get("content", "")
        file = form.get("file")
        if file and hasattr(file, "filename"):
            file_filename = file.filename
        else:
            file = None
    else:
        # Parse JSON body
        body = await request.json()
        session_id = body.get("session_id")
        content = body.get("content", "")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    if not content and not file:
        raise HTTPException(status_code=400, detail="content or file is required")

    # Verify session exists and is active
    session = session_svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") != "active":
        raise HTTPException(status_code=400, detail="Session is no longer active")

    message_content = None   # What we send to Claude (str or list)
    stored_content = ""      # What we store in DB (always str)
    attachment_meta: list[dict] = []
    has_file = False

    if file and file_filename:
        has_file = True
        filename = file_filename
        error = file_processor.validate_file_upload(filename, file.size if hasattr(file, 'size') else None)
        if error:
            raise HTTPException(status_code=400, detail=error)

        saved_path = await file_processor.save_upload_async(file, filename)
        file_data = file_processor.process_file(saved_path, filename)

        # Build multimodal content for Claude
        message_content = anthropic_client.build_multimodal_content(
            content or "", file_data
        )

        # Text representation for DB storage
        if file_data["type"] == "image":
            stored_content = (
                f"{content}\n\n[Attached image: {filename}]"
                if content
                else f"[Attached image: {filename}]"
            )
        else:
            stored_content = (
                f"{content}\n\n[Attached PDF: {filename} — {file_data.get('page_count', '?')} pages]"
                if content
                else f"[Attached PDF: {filename} — {file_data.get('page_count', '?')} pages]"
            )

        attachment_meta = [{
            "filename": filename,
            "type": file_data["type"],
            "size": file_data["size"],
            "storedAs": os.path.basename(saved_path),
            **({"pageCount": file_data["page_count"]} if file_data.get("page_count") else {}),
        }]
    else:
        message_content = content.strip()
        stored_content = content.strip()

    # Store user message
    session_svc.add_message(session_id, "user", stored_content, attachment_meta)

    # Get full conversation history
    db_messages = session_svc.get_messages(session_id)

    # Build Claude messages — use multimodal content for the last message if file
    claude_messages = []
    for idx, m in enumerate(db_messages):
        if idx == len(db_messages) - 1 and has_file:
            claude_messages.append({"role": m["role"], "content": message_content})
        else:
            claude_messages.append({"role": m["role"], "content": m["content"]})

    # Call Claude
    try:
        ai_response = anthropic_client.chat(claude_messages)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {exc}",
        )

    # Store assistant response
    session_svc.add_message(session_id, "assistant", ai_response)

    # Check for intake completion
    is_complete = "[INTAKE_COMPLETE]" in ai_response

    return {
        "role": "assistant",
        "content": ai_response,
        "is_complete": is_complete,
    }


@router.post("/{session_id}/complete")
async def complete_session(session_id: str):
    """Trigger extraction and mark session as completed."""
    session = session_svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        intake = extraction_svc.extract_intake_data(session_id)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {exc}",
        )

    session_svc.update_session_status(session_id, "completed")

    return {
        "message": "Intake extraction complete",
        "intake": intake,
    }
