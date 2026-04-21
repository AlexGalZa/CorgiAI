import functools
import logging
import string
import threading
import uuid
from datetime import date, datetime

import shortuuid
from django.core.cache import cache
from django.db import connection

from common.exceptions import RateLimitError

logger = logging.getLogger(__name__)

_short_uuid = shortuuid.ShortUUID(alphabet=string.ascii_uppercase + string.digits)


def generate_short_id(length: int = 8) -> str:
    return _short_uuid.random(length=length)


def format_currency(amount: int | float) -> str:
    return f"{amount:,.0f}"


def parse_date(v) -> date:
    if isinstance(v, str):
        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
        return dt.date()
    if isinstance(v, datetime):
        return v.date()
    return v


def generate_uuid() -> str:
    return str(uuid.uuid4())


def run_in_background(func, *args, task_name: str = "background_task", **kwargs):
    def wrapper():
        try:
            func(*args, **kwargs)
            logger.info(f"Background task '{task_name}' completed successfully")
        except Exception as e:
            logger.exception(f"Background task '{task_name}' failed: {e}")
        finally:
            connection.close()

    thread = threading.Thread(target=wrapper, name=task_name, daemon=True)
    thread.start()
    return thread


def format_address_street(address) -> str:
    parts = [address.street_address]
    if address.suite:
        parts.append(address.suite)
    return ", ".join(parts)


def format_address_city_state_zip(address) -> str:
    return f"{address.city}, {address.state} {address.zip}"


def format_address(address) -> str:
    return f"{format_address_street(address)}, {format_address_city_state_zip(address)}"


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def rate_limit(max_requests, window_seconds, key_func=None):
    """Throttle a view. Default keys by client IP. Pass `key_func(request)`
    to key by API key, user, tenant, etc.; falls back to IP if key_func
    returns a falsy value."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            bucket = None
            if key_func is not None:
                try:
                    bucket = key_func(request)
                except Exception:
                    bucket = None
            if not bucket:
                bucket = get_client_ip(request)
            key = f"rate_limit:{func.__module__}.{func.__qualname__}:{bucket}"
            count = cache.get(key, 0)
            if count >= max_requests:
                raise RateLimitError()
            cache.set(key, count + 1, window_seconds)
            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def strip_keys_recursive(data: dict, keys: set[str]) -> dict:
    cleaned = {}
    for key, value in data.items():
        if key in keys:
            continue
        if isinstance(value, dict):
            cleaned[key] = strip_keys_recursive(value, keys)
        else:
            cleaned[key] = value
    return cleaned


def stripe_get(obj, key, default=None):
    try:
        return obj[key]
    except (KeyError, TypeError):
        return default


def deep_merge(base: dict, updates: dict) -> dict:
    result = base.copy()
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result
