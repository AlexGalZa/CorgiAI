"""
Shared permission decorators and helpers for API endpoints.

Extracts common authorization patterns used across multiple API modules
into reusable functions. Reduces duplication of org-scoping, role checks,
and staff-only access patterns.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, TypeVar

from ninja.errors import HttpError

from organizations.service import OrganizationService

F = TypeVar("F", bound=Callable[..., Any])


def require_staff(func: F) -> F:
    """Decorator that enforces staff-level access on an endpoint.

    Usage::

        @router.get("/admin-only", auth=JWTAuth())
        @require_staff
        def my_admin_endpoint(request):
            ...

    Raises:
        HttpError: 403 if ``request.auth.is_staff`` is falsy.
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not getattr(user, "is_staff", False):
            raise HttpError(403, "Staff access required")
        return func(request, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def require_editor(func: F) -> F:
    """Decorator that enforces editor (or owner) role in the active org.

    Checks the user's role via ``OrganizationService.can_edit()``.
    Returns a 403 response dict if the user is a viewer or has no membership.

    Usage::

        @router.post("/create-thing", auth=JWTAuth())
        @require_editor
        def create_thing(request, ...):
            ...
    """

    @wraps(func)
    def wrapper(request, *args, **kwargs):
        user = request.auth
        if not OrganizationService.can_edit(user):
            raise HttpError(403, "Editor or owner role required")
        return func(request, *args, **kwargs)

    return wrapper  # type: ignore[return-value]


def get_org_id(request) -> int:
    """Extract the active organization ID from the authenticated request.

    Convenience wrapper around ``OrganizationService.get_active_org_id``
    that reads from ``request.auth``.

    Args:
        request: Django/Ninja request with ``request.auth`` populated by JWTAuth.

    Returns:
        The integer organization ID for the current user context.
    """
    return OrganizationService.get_active_org_id(request.auth)
