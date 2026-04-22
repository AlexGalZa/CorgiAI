import logging
import json
import re
from django.conf import settings
import anthropic

from aib.prompts import SYSTEM_PROMPT, STEP_SUFFIXES, EXTRACTION_PROMPT

logger = logging.getLogger(__name__)


class AibService:
    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self):
        self._client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def chat(self, messages: list[dict], step: str = "get-started") -> tuple[str, dict]:
        """Send conversation to Claude. Returns (reply_text, extracted_fields)."""
        suffix = STEP_SUFFIXES.get(step, "")
        system = [
            {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}},
        ]
        if suffix:
            system.append({"type": "text", "text": suffix})

        try:
            response = self._client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=[{"role": m["role"], "content": m["content"]} for m in messages],
            )
        except anthropic.APIError as exc:
            logger.error("Anthropic API error in chat: %s", exc)
            raise

        text_block = next((b for b in response.content if b.type == "text"), None)
        reply = text_block.text if text_block else ""

        extracted = self.extract_fields(messages + [{"role": "assistant", "content": reply}])
        return reply, extracted

    def extract_fields(self, messages: list[dict]) -> dict:
        """Run extraction prompt over conversation. Returns parsed JSON dict."""
        transcript = "\n\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
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
