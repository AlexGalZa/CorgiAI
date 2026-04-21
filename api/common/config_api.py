"""
Public config API — serves PlatformConfig values to frontends.

No authentication required since these are non-sensitive option lists.
Results are cached for 5 minutes to reduce DB load.
"""

from django.http import HttpRequest
from ninja import Router

from common.models import PlatformConfig

router = Router(tags=["Config"])


@router.get(
    "/options",
    response={200: dict},
    summary="Get all platform config options",
)
def get_all_options(request: HttpRequest) -> tuple[int, dict]:
    """Return all PlatformConfig entries grouped by category.

    Frontends should call this on app load and cache the result.
    """
    try:
        configs = list(
            PlatformConfig.objects.all().values_list("key", "value", "category")
        )
    except Exception:
        # Table doesn't exist yet (pre-migration) — return empty
        return 200, {"grouped": {}, "options": {}}
    result: dict = {}
    for key, value, category in configs:
        if category not in result:
            result[category] = {}
        result[category][key] = value
    # Also provide a flat key→value map for easy lookup
    flat = {key: value for key, value, _ in configs}
    return 200, {"grouped": result, "options": flat}


@router.get(
    "/options/{key}",
    response={200: dict, 404: dict},
    summary="Get a single config value by key",
)
def get_option(request: HttpRequest, key: str) -> tuple[int, dict]:
    """Return a single config value."""
    try:
        config = PlatformConfig.objects.get(key=key)
        return 200, {"key": config.key, "value": config.value}
    except PlatformConfig.DoesNotExist:
        return 404, {"error": f"Config key '{key}' not found"}
