"""
Caching utilities for Corgi platform.

Provides:
- cache_analytics: decorator for analytics endpoint results
- cache_for: decorator for view/function responses with TTL
- cache_model_query: cache a queryset result by key
- invalidate_analytics_cache: clear analytics cache keys
- invalidate_model_cache: clear model-specific cache keys via signals

Cache backend:
    - Redis (via REDIS_URL env var) for production
    - LocMemCache fallback for development/testing
"""

import functools
import hashlib
import logging

from django.core.cache import cache
from django.db.models.signals import post_save, post_delete

logger = logging.getLogger("corgi.cache")

# Prefix for all analytics cache keys
ANALYTICS_PREFIX = "analytics:"

# Prefix for model query caches
MODEL_QUERY_PREFIX = "modelq:"

# Prefix for generic view caches
VIEW_CACHE_PREFIX = "view:"


# ─── Analytics Cache (existing) ──────────────────────────────────────────────


def cache_analytics(timeout: int = 300, key_prefix: str = ""):
    """
    Decorator to cache analytics endpoint results for a given timeout (default 5 min).

    Generates cache key from function name + arguments.
    Skips cache if `?nocache=1` is in the request query params.

    Usage:
        @cache_analytics(timeout=600)
        def get_premium_summary(request, org_id: str):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if request wants to bypass cache
            request = args[0] if args else kwargs.get("request")
            if request and hasattr(request, "GET") and request.GET.get("nocache"):
                return func(*args, **kwargs)

            cache_key = _build_key(func, key_prefix, args[1:], kwargs)

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit: %s", cache_key)
                return cached

            logger.debug("Cache miss: %s", cache_key)
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result

        # Attach cache key builder for external invalidation
        wrapper.cache_key_prefix = key_prefix or func.__name__
        return wrapper

    return decorator


def invalidate_analytics_cache(pattern: str = ""):
    """
    Invalidate analytics cache entries.

    If pattern is empty, attempts to clear all analytics keys.
    If pattern is provided, deletes keys matching that pattern.

    Call this after data mutations that affect analytics results.

    Usage:
        invalidate_analytics_cache()                    # clear all analytics
        invalidate_analytics_cache("premium_summary")   # clear specific
    """
    if pattern:
        key = f"{ANALYTICS_PREFIX}{pattern}"
        cache.delete(key)
        logger.info("Invalidated cache key: %s", key)
    else:
        # Django's cache backend doesn't support pattern deletion natively.
        # For Redis, you'd use cache.delete_pattern(f"{ANALYTICS_PREFIX}*")
        # For LocMemCache / fallback, we track known keys.
        try:
            # Redis backend with django-redis
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern(f"{ANALYTICS_PREFIX}*")
                logger.info("Invalidated all analytics cache (pattern)")
                return
        except Exception:
            pass

        # Fallback: log a warning — caller should pass specific patterns
        logger.warning(
            "Cannot bulk-invalidate analytics cache without Redis. "
            "Pass a specific pattern or use Redis as cache backend."
        )


def _build_key(func, prefix: str, args: tuple, kwargs: dict) -> str:
    """Build a deterministic cache key from function signature + arguments."""
    parts = [prefix or func.__name__]

    for arg in args:
        parts.append(str(arg))

    for k in sorted(kwargs.keys()):
        if k == "request":
            continue
        parts.append(f"{k}={kwargs[k]}")

    raw = ":".join(parts)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{ANALYTICS_PREFIX}{func.__name__}:{hashed}"


# ─── Generic View/Function Cache Decorator ───────────────────────────────────


def cache_for(seconds: int, key_prefix: str = ""):
    """
    Decorator to cache any function's return value for N seconds.

    The cache key is derived from the function name + all positional/keyword
    arguments. Request objects are fingerprinted by their path+query string.

    Skips cache if the first argument is a request with `?nocache=1`.

    Usage:
        @cache_for(300)
        def get_coverage_options(coverage_type: str):
            ...

        @cache_for(60, key_prefix="forms")
        def get_form_definition(slug: str):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Bypass check
            first = args[0] if args else None
            if first is not None and hasattr(first, "GET"):
                if first.GET.get("nocache"):
                    return func(*args, **kwargs)

            cache_key = _build_view_key(func, key_prefix, args, kwargs)

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("cache_for hit: %s", cache_key)
                return cached

            logger.debug("cache_for miss: %s", cache_key)
            result = func(*args, **kwargs)
            cache.set(cache_key, result, seconds)
            return result

        wrapper._cache_key_prefix = key_prefix or func.__name__
        wrapper._cache_ttl = seconds
        return wrapper

    return decorator


def invalidate_cache_for(func_or_prefix: str, *args, **kwargs):
    """
    Invalidate a specific cache_for key.

    Pass the same arguments you would call the function with to derive the key.

    Usage:
        invalidate_cache_for("get_coverage_options", "tech-e-and-o")
    """
    prefix = (
        func_or_prefix if isinstance(func_or_prefix, str) else func_or_prefix.__name__
    )
    raw_parts = (
        [prefix]
        + [str(a) for a in args]
        + [f"{k}={v}" for k, v in sorted(kwargs.items())]
    )
    raw = ":".join(raw_parts)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
    key = f"{VIEW_CACHE_PREFIX}{prefix}:{hashed}"
    cache.delete(key)
    logger.info("Invalidated cache key: %s", key)


def _build_view_key(func, prefix: str, args: tuple, kwargs: dict) -> str:
    """Build cache key for cache_for decorator."""
    parts = [prefix or func.__name__]

    for arg in args:
        # Fingerprint request objects by path+query
        if hasattr(arg, "path") and hasattr(arg, "GET"):
            from urllib.parse import urlencode

            parts.append(f"req:{arg.path}?{urlencode(arg.GET)}")
        else:
            parts.append(str(arg))

    for k in sorted(kwargs.keys()):
        parts.append(f"{k}={kwargs[k]}")

    raw = ":".join(parts)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{VIEW_CACHE_PREFIX}{func.__name__}:{hashed}"


# ─── Model Query Cache ────────────────────────────────────────────────────────


def cache_model_query(queryset, key: str, ttl: int = 300):
    """
    Cache a queryset result by an explicit key.

    Evaluates the queryset (if not already) and stores the result list.
    Returns the cached list on subsequent calls.

    Usage:
        def get_coverage_options(coverage_type: str):
            qs = CoverageOption.objects.filter(coverage_type=coverage_type)
            return cache_model_query(qs, f"coverage_opts:{coverage_type}", ttl=600)
    """
    full_key = f"{MODEL_QUERY_PREFIX}{key}"

    cached = cache.get(full_key)
    if cached is not None:
        logger.debug("cache_model_query hit: %s", full_key)
        return cached

    logger.debug("cache_model_query miss: %s", full_key)
    result = list(queryset)
    cache.set(full_key, result, ttl)
    return result


def invalidate_model_query_cache(key: str):
    """Invalidate a specific model query cache entry."""
    full_key = f"{MODEL_QUERY_PREFIX}{key}"
    cache.delete(full_key)
    logger.info("Invalidated model query cache: %s", full_key)


# ─── Signal-based Cache Invalidation ─────────────────────────────────────────

_model_cache_registry: dict = {}
# Maps: Model class → list of (key_pattern, prefix)


def register_model_cache_invalidation(model_class, cache_key_prefix: str):
    """
    Register a model for automatic cache invalidation on save/delete.

    When any instance of model_class is saved or deleted, all cache keys
    matching cache_key_prefix are invalidated.

    Usage:
        register_model_cache_invalidation(FormDefinition, "formdef:")
        register_model_cache_invalidation(RatingFactor, "rating_factor:")
    """
    if model_class not in _model_cache_registry:
        _model_cache_registry[model_class] = []
        _connect_invalidation_signals(model_class)

    if cache_key_prefix not in _model_cache_registry[model_class]:
        _model_cache_registry[model_class].append(cache_key_prefix)
        logger.debug(
            "Registered cache invalidation: %s → %s",
            model_class.__name__,
            cache_key_prefix,
        )


def _connect_invalidation_signals(model_class):
    """Connect post_save and post_delete signals for cache invalidation."""

    def _invalidate(sender, instance, **kwargs):
        prefixes = _model_cache_registry.get(sender, [])
        for prefix in prefixes:
            _bulk_invalidate(prefix)

    post_save.connect(_invalidate, sender=model_class, weak=False)
    post_delete.connect(_invalidate, sender=model_class, weak=False)


def _bulk_invalidate(prefix: str):
    """
    Delete all cache keys starting with prefix.
    Uses Redis pattern delete if available, otherwise single-key delete.
    """
    full_prefix = f"{MODEL_QUERY_PREFIX}{prefix}"
    try:
        if hasattr(cache, "delete_pattern"):
            cache.delete_pattern(f"{full_prefix}*")
            logger.info("Bulk invalidated cache pattern: %s*", full_prefix)
        else:
            # LocMemCache: delete the exact key (best effort)
            cache.delete(full_prefix)
            logger.debug("Invalidated single cache key: %s", full_prefix)
    except Exception as exc:
        logger.warning("Cache invalidation failed for %s: %s", full_prefix, exc)


# ─── Pre-wire common model invalidations ─────────────────────────────────────
# Called from common/apps.py ready() to wire up signals after models are loaded.


def setup_model_cache_invalidations():
    """
    Register model-level cache invalidation for heavy query targets.

    Called from CommonConfig.ready() after all apps are loaded.
    """
    try:
        from forms.models import FormDefinition

        register_model_cache_invalidation(FormDefinition, "formdef:")
        logger.info("Cache invalidation wired: FormDefinition")
    except ImportError:
        pass

    try:
        from rating.rules import COVERAGE_DEFINITIONS  # noqa — just confirm import

        # RatingService uses in-memory rules; no DB model to watch.
        # If a RatingFactor model is added later, wire it here.
        logger.debug("Rating rules are static; no DB cache invalidation needed")
    except ImportError:
        pass
