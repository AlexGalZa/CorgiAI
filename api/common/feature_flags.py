"""
Feature flags system for the Corgi platform.

Provides runtime feature toggles with:
- Per-flag enable/disable
- Percentage-based rollout
- Org-specific allowlists
- Staff-only flags
- Template tags for frontend/admin use

The FeatureFlag model is defined in common/models.py to avoid circular imports.

Usage:
    from common.feature_flags import is_enabled

    if is_enabled("new_portal_dashboard", user=request.user, org=current_org):
        ...
"""

import hashlib
import logging

logger = logging.getLogger("corgi.feature_flags")


# ─── Seed flag definitions ───────────────────────────────────────────────────

SEED_FLAGS = [
    {
        "key": "new_portal_dashboard",
        "description": "Enable the redesigned V3 portal dashboard with KPI cards and pipeline view.",
        "is_enabled": False,
        "rollout_percentage": 0,
        "staff_only": False,
    },
    {
        "key": "renewal_flow",
        "description": "Enable the automated renewal flow with email triggers and proposal generation.",
        "is_enabled": False,
        "rollout_percentage": 0,
        "staff_only": False,
    },
    {
        "key": "self_serve_limits",
        "description": "Allow customers to self-serve limit and retention changes without underwriter approval.",
        "is_enabled": False,
        "rollout_percentage": 0,
        "staff_only": False,
    },
    {
        "key": "slack_notifications",
        "description": "Send Slack notifications for key events (quote ready, claim filed, payment failed).",
        "is_enabled": False,
        "rollout_percentage": 0,
        "staff_only": True,
    },
]


# ─── Service ─────────────────────────────────────────────────────────────────


def is_enabled(flag_key: str, user=None, org=None) -> bool:
    """
    Check if a feature flag is enabled for the given user/org context.

    Resolution order:
    1. Flag doesn't exist → False
    2. Flag.is_enabled is False → False
    3. Flag.staff_only and user is not staff → False
    4. Org in allowed_orgs → True
    5. rollout_percentage == 100 → True
    6. rollout_percentage == 0 → False
    7. Percentage rollout check (deterministic hash by org or user id)

    Args:
        flag_key: The unique flag key
        user: Optional Django user object
        org: Optional Organization object

    Returns:
        True if the flag is active for this context
    """
    from common.models import FeatureFlag

    try:
        flag = FeatureFlag.objects.get(key=flag_key)
    except FeatureFlag.DoesNotExist:
        logger.debug("Feature flag not found: %s", flag_key)
        return False

    # Master switch
    if not flag.is_enabled:
        return False

    # Staff gate
    if flag.staff_only:
        if user is None or not getattr(user, "is_staff", False):
            return False

    # Org allowlist
    if org is not None:
        if flag.allowed_orgs.filter(id=org.id).exists():
            return True

    # 100% rollout — everyone
    if flag.rollout_percentage >= 100:
        return True

    # 0% rollout — nobody (unless in allowlist, already handled above)
    if flag.rollout_percentage == 0:
        return False

    # Percentage rollout — deterministic hash
    bucket_id = None
    if org is not None:
        bucket_id = str(org.id)
    elif user is not None:
        bucket_id = str(user.id)

    if bucket_id is None:
        # No identity to hash — fall back to disabled
        return False

    hash_input = f"{flag_key}:{bucket_id}".encode("utf-8")
    hash_int = int(hashlib.md5(hash_input).hexdigest(), 16)
    bucket = hash_int % 100  # 0–99

    return bucket < flag.rollout_percentage


def get_all_flags(user=None, org=None) -> dict:
    """
    Return a dict of {flag_key: bool} for all flags.
    Useful for passing to frontend as a flags context.
    """
    from common.models import FeatureFlag

    return {
        flag.key: is_enabled(flag.key, user=user, org=org)
        for flag in FeatureFlag.objects.all()
    }
