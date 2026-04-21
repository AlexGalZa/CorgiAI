"""
Shared API utility functions.

Provides helpers for parsing multipart form data JSON payloads
with Pydantic schema validation, used across quote and claim
submission endpoints.
"""

import json
import logging
from ninja.errors import HttpError
from pydantic import ValidationError

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

logger = logging.getLogger(__name__)


def parse_form_data_json(json_str: str, schema_class):
    try:
        data = json.loads(json_str)
        return schema_class(**data)
    except json.JSONDecodeError:
        raise HttpError(400, "Invalid JSON format in data")
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        if sentry_sdk:
            sentry_sdk.capture_exception(e)
        raise HttpError(400, f"Validation error: {e.errors()}")
