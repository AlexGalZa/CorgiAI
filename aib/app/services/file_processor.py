"""
File upload validation, processing, and storage.
Mirrors the file-handling logic from server/src/routes/chat.js
"""

from __future__ import annotations
import base64
import mimetypes
import os
import time
import math
import random
import shutil

from PyPDF2 import PdfReader
from app import config


def validate_file(filepath: str, filename: str) -> str | None:
    """
    Return an error message if the file is invalid, or None if OK.
    Validates a file already on disk (used by Gradio path).
    """
    mime, _ = mimetypes.guess_type(filename)
    if mime not in config.ALLOWED_MIME_TYPES:
        return "Only JPG, JPEG, PNG, and PDF files are allowed."

    size = os.path.getsize(filepath)
    if size > config.MAX_FILE_SIZE:
        return f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024 * 1024)} MB."

    return None


def validate_file_upload(filename: str, size: int | None = None) -> str | None:
    """
    Validate a file upload by name and optional size (for FastAPI UploadFile).
    Returns an error message or None if OK.
    """
    mime, _ = mimetypes.guess_type(filename)
    if mime not in config.ALLOWED_MIME_TYPES:
        return "Only JPG, JPEG, PNG, and PDF files are allowed."

    if size is not None and size > config.MAX_FILE_SIZE:
        return f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024 * 1024)} MB."

    return None


def save_upload(filepath: str, original_name: str) -> str:
    """
    Copy an uploaded file into the uploads/ directory with a unique name.
    Returns the destination path.
    """
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    ext = os.path.splitext(original_name)[1]
    unique = f"{int(time.time())}-{math.floor(random.random() * 1e9)}{ext}"
    dest = os.path.join(config.UPLOADS_DIR, unique)
    shutil.copy2(filepath, dest)
    return dest


async def save_upload_async(upload_file, original_name: str) -> str:
    """
    Save a FastAPI UploadFile to the uploads/ directory with a unique name.
    Returns the destination path.
    """
    os.makedirs(config.UPLOADS_DIR, exist_ok=True)
    ext = os.path.splitext(original_name)[1]
    unique = f"{int(time.time())}-{math.floor(random.random() * 1e9)}{ext}"
    dest = os.path.join(config.UPLOADS_DIR, unique)

    content = await upload_file.read()
    with open(dest, "wb") as f:
        f.write(content)

    return dest


def process_file(filepath: str, filename: str) -> dict:
    """
    Process an uploaded file for Claude.

    Returns a dict with:
      - type: "image" | "pdf"
      - filename: original name
      - size: bytes
      For images:  base64, media_type
      For PDFs:    extracted_text, page_count
    """
    mime, _ = mimetypes.guess_type(filename)
    category = config.ALLOWED_MIME_TYPES.get(mime)
    size = os.path.getsize(filepath)

    if category == "image":
        with open(filepath, "rb") as f:
            raw = f.read()
        return {
            "type": "image",
            "filename": filename,
            "media_type": mime,
            "base64": base64.b64encode(raw).decode("ascii"),
            "size": size,
        }

    if category == "pdf":
        reader = PdfReader(filepath)
        text_parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
        return {
            "type": "pdf",
            "filename": filename,
            "extracted_text": "\n".join(text_parts),
            "page_count": len(reader.pages),
            "size": size,
        }

    raise ValueError(f"Unsupported file type: {mime}")
