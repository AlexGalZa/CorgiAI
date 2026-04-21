"""
Claude API wrapper — chat, extraction, and multimodal content building.
Mirrors server/src/services/anthropic.js
"""

from __future__ import annotations
import json
import re
import anthropic
from app import config
from app.prompts.system import SYSTEM_PROMPT

_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096


def chat(messages: list[dict]) -> str:
    """
    Send a conversation to Claude and return the assistant's text response.

    Each message in *messages* has:
      - role: "user" | "assistant"
      - content: str  OR  list of content blocks (multimodal)
    """
    response = _client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": m["role"], "content": m["content"]} for m in messages],
    )
    text_block = next((b for b in response.content if b.type == "text"), None)
    return text_block.text if text_block else ""


def build_multimodal_content(user_text: str, file_data: dict) -> list[dict]:
    """
    Build a content-block array for a user message that includes a file.

    *file_data* keys:
      - type: "image" | "pdf"
      - filename: str
      - base64: str          (images only)
      - media_type: str      (images only)
      - extracted_text: str   (PDFs only)
    """
    blocks: list[dict] = []

    if file_data["type"] == "image":
        blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": file_data["media_type"],
                "data": file_data["base64"],
            },
        })
    elif file_data["type"] == "pdf":
        blocks.append({
            "type": "text",
            "text": (
                f"[UPLOADED DOCUMENT: {file_data['filename']}]\n\n"
                f"{file_data['extracted_text']}\n\n"
                "[END DOCUMENT]"
            ),
        })

    text = (user_text or "").strip()
    if not text:
        text = (
            "Please analyze this insurance document. Identify the policies, "
            "coverages, limits, and any other key details. Then recommend "
            "additional coverages based on what you see."
        )

    blocks.append({"type": "text", "text": text})
    return blocks


def extract(extraction_prompt: str) -> dict:
    """
    Run an extraction prompt and return parsed JSON.
    """
    response = _client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": extraction_prompt}],
    )
    text_block = next((b for b in response.content if b.type == "text"), None)
    raw = text_block.text if text_block else "{}"

    # Strip markdown fences if present
    cleaned = re.sub(r"```json\n?", "", raw)
    cleaned = re.sub(r"```\n?", "", cleaned).strip()
    return json.loads(cleaned)
