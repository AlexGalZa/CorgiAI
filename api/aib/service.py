import base64
import logging
import json
import re
from typing import Optional
from django.conf import settings
import anthropic

from aib.prompts import SYSTEM_PROMPT, STEP_SUFFIXES, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
SUPPORTED_DOC_TYPES = {"application/pdf"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


class AibService:
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def chat(
        self,
        messages: list[dict],
        step: str = "get-started",
        file_data: Optional[dict] = None,
    ) -> tuple[str, dict]:
        """Send conversation to Claude. Returns (reply_text, extracted_fields).

        file_data (optional): {"media_type": str, "data": bytes, "file_name": str}
        The file is attached only to the final user turn; history stays text-only
        so extract_fields and session replay are unaffected.
        """
        suffix = STEP_SUFFIXES.get(step, "")
        system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        ]
        if suffix:
            system.append({"type": "text", "text": suffix})

        claude_messages = []
        for i, m in enumerate(messages):
            is_last = i == len(messages) - 1
            if is_last and m["role"] == "user" and file_data:
                claude_messages.append(
                    {"role": "user", "content": _build_file_content(m["content"], file_data)}
                )
            else:
                claude_messages.append({"role": m["role"], "content": m["content"]})

        try:
            response = self._client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=claude_messages,
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error in chat: %s", exc)
            raise

        text_block = next((b for b in response.content if b.type == "text"), None)
        reply = text_block.text if text_block else ""

        # Pass text-only history to extraction so it stays robust regardless of file content.
        extracted = self.extract_fields(messages + [{"role": "assistant", "content": reply}])
        return reply, extracted

    def extract_fields(self, messages: list[dict]) -> dict:
        """Run extraction prompt over conversation. Returns parsed JSON dict."""
        transcript = "\n\n".join(
            f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else '[file attachment]'}"
            for m in messages
        )
        full_prompt = EXTRACTION_PROMPT + transcript
        try:
            response = self._client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                messages=[{"role": "user", "content": full_prompt}],
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error in extract_fields: %s", exc)
            raise

        text_block = next((b for b in response.content if b.type == "text"), None)
        raw = text_block.text if text_block else "{}"
        cleaned = re.sub(r"```json\n?", "", raw)
        cleaned = re.sub(r"```\n?", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            logger.warning("extract_fields: failed to parse JSON. raw=%r", raw[:200])
            return {}


def _build_file_content(text: str, file_data: dict) -> list:
    """Build a multimodal content block list for a user message with an attached file."""
    media_type = file_data["media_type"]
    encoded = base64.standard_b64encode(file_data["data"]).decode("utf-8")

    if media_type in SUPPORTED_IMAGE_TYPES:
        file_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }
    else:
        file_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": encoded},
        }

    blocks = [file_block]
    if text:
        blocks.append({"type": "text", "text": text})
    return blocks
