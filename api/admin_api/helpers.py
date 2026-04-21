"""
Shared helpers and role constants for the Admin API.

Provides:
- Role constant lists for RBAC checks.
- ``_require_staff`` / ``_require_role`` auth helpers.
- ``_scope_queryset_by_role`` for broker-level data scoping.
- ``_get_broker_partner_ids`` to resolve broker ↔ ReferralPartner links.
"""

import logging

from django.http import HttpRequest
from ninja.errors import HttpError

logger = logging.getLogger(__name__)


# ── Role constants ───────────────────────────────────────────────────

ADMIN_ROLES = ["admin"]
WRITE_ROLES = ["ae", "ae_underwriting", "admin"]
OPERATIONS_ROLES = ["ae", "ae_underwriting", "admin"]
FINANCE_ROLES = ["finance", "admin"]
UNDERWRITING_ROLES = ["ae_underwriting", "admin"]
ALL_STAFF_ROLES = [
    "bdr",
    "ae",
    "ae_underwriting",
    "finance",
    "broker",
    "admin",
    "claims_adjuster",
    "customer_support",
]
CLAIMS_ROLES = ["claims_adjuster", "ae", "ae_underwriting", "admin"]
SUPPORT_ROLES = ["customer_support", "ae", "ae_underwriting", "admin"]


# ── Data scoping helpers ─────────────────────────────────────────────


def _get_broker_partner_ids(user) -> list[int]:
    """Return ReferralPartner IDs whose notification_emails include the user's email.

    This links a broker staff user to their ReferralPartner record(s) so
    we can scope querysets to only show data belonging to their referral pipeline.
    """
    from quotes.models import ReferralPartner

    email = getattr(user, "email", "")
    if not email:
        return []
    # notification_emails is a JSONField list — __contains works on PostgreSQL
    return list(
        ReferralPartner.objects.filter(
            notification_emails__contains=[email],
        ).values_list("id", flat=True)
    )


def _scope_queryset_by_role(qs, user, model_name: str):
    """Filter a queryset based on the authenticated user's role.

    Brokers only see records linked to their referral partner(s).
    All other staff roles see everything they have endpoint access to.

    Args:
        qs: The base queryset (already filtered by search/status/etc.).
        user: The authenticated user from ``request.auth``.
        model_name: One of 'quotes', 'policies', 'brokered_requests'.

    Returns:
        The (possibly narrowed) queryset.
    """
    role = getattr(user, "role", "")
    if role == "broker":
        partner_ids = _get_broker_partner_ids(user)
        if not partner_ids:
            # Broker with no linked partner sees nothing
            return qs.none()
        if model_name == "quotes":
            return qs.filter(referral_partner_id__in=partner_ids)
        elif model_name == "policies":
            return qs.filter(quote__referral_partner_id__in=partner_ids)
        elif model_name == "brokered_requests":
            return qs.filter(quote__referral_partner_id__in=partner_ids)
    # BDR, AE, Finance, Admin — see everything they have endpoint access to
    return qs


# ── Auth helpers ─────────────────────────────────────────────────────


def _require_staff(request: HttpRequest) -> None:
    """Raise 403 if the authenticated user is not staff.

    Args:
        request: The incoming HTTP request with ``request.auth`` set by JWTAuth.

    Raises:
        HttpError: 403 if the user lacks ``is_staff``.
    """
    user = request.auth
    if not getattr(user, "is_staff", False):
        raise HttpError(403, "Staff access required")


def _require_role(
    request: HttpRequest, allowed_roles: list[str], action: str = ""
) -> None:
    """Raise 403 if the authenticated staff user's role is not in allowed_roles.

    Superusers bypass the role check. Logs failed attempts.

    Args:
        request: The incoming HTTP request with ``request.auth`` set by JWTAuth.
        allowed_roles: List of role strings permitted for this action.
        action: Description of the attempted action (for logging).

    Raises:
        HttpError: 403 if the user lacks ``is_staff`` or their role is not allowed.
    """
    _require_staff(request)
    user = request.auth
    role = getattr(user, "role", "")
    if role not in allowed_roles and not getattr(user, "is_superuser", False):
        email = getattr(user, "email", "unknown")
        logger.info(
            "RBAC denied: user=%s role=%s attempted_action=%s allowed_roles=%s",
            email,
            role,
            action or "unspecified",
            allowed_roles,
        )
        raise HttpError(
            403, f"Your role ({role}) does not have permission for this action"
        )
