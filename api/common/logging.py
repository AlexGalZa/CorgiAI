"""
Structured JSON logging for production.

Provides a JSON formatter that includes request context (user_id, org_id,
request_id) in every log entry for easy searching in CloudWatch / ELK.
"""

import json
import logging
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON for structured logging.

    Output example:
    {"timestamp":"2026-03-28T20:00:00Z","level":"INFO","logger":"corgi.api",
     "message":"GET /api/v1/quotes 200","request_id":"abc123","user_id":"42"}
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Request context (set by middleware or manually)
        for attr in ("correlation_id", "request_id", "user_id", "org_id"):
            value = getattr(record, attr, None)
            if value:
                log_entry[attr] = str(value)

        # Module location
        if record.pathname:
            log_entry["module"] = f"{record.pathname}:{record.lineno}"

        # Exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__
                if record.exc_info[0]
                else "Unknown",
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        # Extra fields
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, default=str, ensure_ascii=False)


class RequestContextFilter(logging.Filter):
    """
    Injects request context into log records from thread-local storage.

    Use with Django middleware that sets threading.local() values.
    Falls back to empty strings if no request context is available.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        import threading

        ctx = getattr(threading.local(), "request_context", {})

        record.correlation_id = getattr(record, "correlation_id", None) or ctx.get(
            "correlation_id", ""
        )
        record.request_id = getattr(record, "request_id", None) or ctx.get(
            "request_id", ""
        )
        record.user_id = getattr(record, "user_id", None) or ctx.get("user_id", "")
        record.org_id = getattr(record, "org_id", None) or ctx.get("org_id", "")

        return True


# ---------- Django LOGGING dict config ----------


def get_logging_config(debug: bool = False) -> dict:
    """
    Returns a Django LOGGING dict-config suitable for settings.py.

    Usage in settings.py:
        from common.logging import get_logging_config
        LOGGING = get_logging_config(DEBUG)
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": "common.logging.RequestContextFilter",
            },
        },
        "formatters": {
            "json": {
                "()": "common.logging.JSONFormatter",
            },
            "verbose": {
                "format": "[{asctime}] {levelname} {name} {message}",
                "style": "{",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose" if debug else "json",
                "filters": ["request_context"],
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "DEBUG" if debug else "INFO",
        },
        "loggers": {
            "django": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False,
            },
            "django.request": {
                "handlers": ["console"],
                "level": "WARNING",
                "propagate": False,
            },
            "corgi": {
                "handlers": ["console"],
                "level": "DEBUG" if debug else "INFO",
                "propagate": False,
            },
        },
    }
