"""
Policy API endpoints for the Corgi Insurance portal.

Provides read-only access to policies, COI downloads, coverage
recommendations, billing overview, Stripe billing portal access,
and policy renewal endpoints.
All endpoints require JWT authentication and are org-scoped.
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router

from ninja import Schema
from pydantic import field_validator

from policies.service import PolicyService
from policies.renewal_service import PolicyRenewalService
from policies.models import Policy, CoverageModificationRequest, ReviewSchedule
from common.schemas import ApiResponseSchema
from users.auth import JWTAuth

router = Router(tags=["Policies"])


@router.get("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_user_policies(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all active policies for the current organization.

    Returns policy details including coverage type, premium, billing
    frequency, effective/expiration dates, associated documents, and
    carrier information.

    Returns:
        200 with a list of policy detail dicts.
    """
    policies = PolicyService.get_policies_for_user(request.auth)
    return 200, {
        "success": True,
        "message": "Policies retrieved successfully",
        "data": policies,
    }


# ── Policy Address / Company Name Edit (V3 #5.4) ──────────────────────────────


class PolicyAddressSchema(Schema):
    street: str
    suite: str = ""
    city: str
    state: str
    zip: str

    @field_validator("street", "city", "state", "zip")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("state")
    @classmethod
    def state_two_letter(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 2:
            raise ValueError("State must be a 2-letter code")
        return v


class PolicyEditSchema(Schema):
    """Only ``address`` and ``company_name`` are accepted — all other
    fields on the payload are silently ignored (strict allowlist)."""

    address: PolicyAddressSchema | None = None
    company_name: str | None = None

    @field_validator("company_name")
    @classmethod
    def company_name_not_blank(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Company name cannot be empty")
        return v


@router.get(
    "/{policy_number}/coi",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema},
)
def download_coi(
    request: HttpRequest, policy_number: str
) -> tuple[int, dict[str, Any]]:
    """Get a presigned S3 download URL for a policy's Certificate of Insurance.

    Args:
        request: HTTP request with JWT-authenticated user.
        policy_number: The policy number to look up.

    Returns:
        200 with download URL and filename, or 404 if not found.
    """
    try:
        data = PolicyService.get_coi_download_url(policy_number, request.auth)
        return 200, {"success": True, "message": "Download URL generated", "data": data}
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}
    except ValueError as e:
        return 404, {"success": False, "message": str(e), "data": None}


@router.get("/recommendations", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_coverage_recommendations(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Recommend additional coverage types the user doesn't own yet.

    Returns up to 2 instant-rated coverage slugs that are not already
    covered by active policies in the user's organization.

    Returns:
        200 with a list of recommended coverage slugs.
    """
    recommendations = PolicyService.get_recommended_coverages(request.auth)
    return 200, {
        "success": True,
        "message": "Recommendations retrieved successfully",
        "data": recommendations,
    }


@router.get("/billing", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_billing_info(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Get billing overview for the current user.

    Returns the user's payment method on file, active payment plans
    (per policy), and recent payment history from Stripe.

    Returns:
        200 with billing info dict (has_billing, payment_method, plans, history).
    """
    try:
        billing_info = PolicyService.get_billing_info(request.auth)
    except Exception:
        # Stripe not configured or no billing data — return empty state
        billing_info = {
            "has_billing": False,
            "payment_method": None,
            "plans": [],
            "history": [],
        }
    return 200, {
        "success": True,
        "message": "Billing info retrieved successfully",
        "data": billing_info,
    }


@router.post(
    "/billing/portal",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 400: ApiResponseSchema},
)
def get_billing_portal_url(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Generate a Stripe billing portal URL for managing payment methods.

    The portal allows customers to update their payment method and
    view invoice history. Subscription cancellation and plan changes
    are disabled.

    Returns:
        200 with the portal URL, or 400 if no billing info exists.
    """
    try:
        portal_url = PolicyService.get_billing_portal_url(request.auth)
    except Exception:
        portal_url = None
    if not portal_url:
        return 400, {
            "success": False,
            "message": "No billing information found",
            "data": None,
        }
    return 200, {
        "success": True,
        "message": "Portal URL generated successfully",
        "data": {"url": portal_url},
    }


# ── Policy Renewal Endpoints ──────────────────────────────────────────────────


@router.get(
    "/{policy_id}/renewal",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema, 403: ApiResponseSchema},
)
def get_renewal_data(
    request: HttpRequest, policy_id: int
) -> tuple[int, dict[str, Any]]:
    """Get renewal data for a policy, pre-filled with current policy information.

    Returns renewal offer details including the existing policy's coverage,
    limits, premium estimate, and the renewal record if one exists.

    Args:
        request: HTTP request with JWT-authenticated user.
        policy_id: Primary key of the policy.

    Returns:
        200 with renewal data dict, 404 if not found, 403 if not authorized.
    """
    try:
        data = PolicyRenewalService.get_renewal_data(policy_id, request.auth)
        return 200, {
            "success": True,
            "message": "Renewal data retrieved successfully",
            "data": data,
        }
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}
    except PermissionError as e:
        return 403, {"success": False, "message": str(e), "data": None}


@router.post(
    "/{policy_id}/renew",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        404: ApiResponseSchema,
        403: ApiResponseSchema,
        400: ApiResponseSchema,
    },
)
def accept_renewal(request: HttpRequest, policy_id: int) -> tuple[int, dict[str, Any]]:
    """Accept a renewal offer for a policy.

    Creates a checkout URL for the renewal. The customer is redirected
    to Stripe to complete payment, after which a new policy is created.

    Args:
        request: HTTP request with JWT-authenticated user.
        policy_id: Primary key of the policy being renewed.

    Returns:
        200 with checkout URL, 404 if not found, 400 if renewal not available.
    """
    try:
        data = PolicyRenewalService.initiate_renewal_checkout(policy_id, request.auth)
        return 200, {
            "success": True,
            "message": "Renewal checkout initiated",
            "data": data,
        }
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}
    except PermissionError as e:
        return 403, {"success": False, "message": str(e), "data": None}
    except ValueError as e:
        return 400, {"success": False, "message": str(e), "data": None}


# ── Policy Reinstatement (6.5) ────────────────────────────────────────────────

# HMAC-signed token helpers. We use Django's TimestampSigner — which wraps
# HMAC-SHA256 of SECRET_KEY + a namespace salt — so the token is:
#   base64url(payload):base64url(timestamp):base64url(hmac)
# Payload is the bare policy id; the salt "policy-reinstatement" namespaces
# the key so the token only validates for this flow. Tokens expire in 30 days.
REINSTATEMENT_TOKEN_SALT = "policy-reinstatement"
REINSTATEMENT_TOKEN_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def _make_reinstatement_signer():
    from django.core.signing import TimestampSigner

    return TimestampSigner(salt=REINSTATEMENT_TOKEN_SALT)


def generate_reinstatement_token(policy_id: int) -> str:
    """Generate an HMAC-SHA256-signed, timestamped, policy-bound token."""
    return _make_reinstatement_signer().sign(str(policy_id))


def decode_reinstatement_token(token: str) -> int:
    """Validate token and return the policy id. Raises BadSignature/SignatureExpired."""
    from django.core.signing import SignatureExpired, BadSignature

    try:
        raw = _make_reinstatement_signer().unsign(
            token, max_age=REINSTATEMENT_TOKEN_MAX_AGE
        )
        return int(raw)
    except (SignatureExpired, BadSignature, ValueError) as e:
        raise BadSignature(f"Invalid reinstatement token: {e}")


@router.get(
    "/{policy_id}/reinstatement-token",
    auth=JWTAuth(),
    response={200: ApiResponseSchema, 404: ApiResponseSchema, 403: ApiResponseSchema},
    summary="Generate a one-time HMAC-signed reinstatement token for a policy",
)
def get_reinstatement_token(
    request: HttpRequest, policy_id: int
) -> tuple[int, dict[str, Any]]:
    """Generate an HMAC-SHA256-signed, timestamped token bound to a policy id.

    Used to build the deep link in the reinstatement email. The token is
    produced with Django's ``TimestampSigner`` (salt='policy-reinstatement')
    and expires 30 days after issuance.
    """
    from organizations.service import OrganizationService

    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    token = generate_reinstatement_token(policy.pk)
    return 200, {
        "success": True,
        "message": "Reinstatement token generated",
        "data": {
            "token": token,
            "policy_id": policy.pk,
            "policy_number": policy.policy_number,
            "expires_in_seconds": REINSTATEMENT_TOKEN_MAX_AGE,
        },
    }


@router.post(
    "/{policy_id}/reinstate",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        404: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
    },
    summary="Reinstate a cancelled policy by resuming its Stripe subscription",
)
def reinstate_policy(
    request: HttpRequest, policy_id: int
) -> tuple[int, dict[str, Any]]:
    """Reinstate a cancelled policy.

    Resumes the underlying Stripe subscription (``Subscription.resume`` for
    paused subs, or clears ``cancel_at``/``cancel_at_period_end`` for
    scheduled cancellations). Flips ``Policy.status`` back to ``'active'``.
    """
    import logging
    from organizations.service import OrganizationService
    from stripe_integration.service import StripeService

    logger = logging.getLogger(__name__)

    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if policy.status == "active":
        return 200, {
            "success": True,
            "message": "Policy is already active",
            "data": {"policy_number": policy.policy_number, "status": policy.status},
        }

    if policy.status not in ("cancelled", "past_due"):
        return 400, {
            "success": False,
            "message": f"Cannot reinstate a {policy.status} policy",
            "data": None,
        }

    if not policy.stripe_subscription_id:
        return 400, {
            "success": False,
            "message": "Policy has no Stripe subscription to resume",
            "data": None,
        }

    # Resume / un-cancel the Stripe subscription.
    try:
        client = StripeService.get_client()
        sub = client.Subscription.retrieve(policy.stripe_subscription_id)
        sub_status = (
            sub.get("status") if isinstance(sub, dict) else getattr(sub, "status", None)
        )

        if sub_status == "paused":
            client.Subscription.resume(policy.stripe_subscription_id)
        elif sub_status == "canceled":
            # Fully cancelled subs cannot be resumed — they must be re-created.
            return 400, {
                "success": False,
                "message": (
                    "Subscription has been fully cancelled and cannot be resumed. "
                    "Please start a new quote to purchase a fresh policy."
                ),
                "data": None,
            }
        else:
            # Scheduled cancellation (cancel_at / cancel_at_period_end) — clear it.
            client.Subscription.modify(
                policy.stripe_subscription_id,
                cancel_at_period_end=False,
                cancel_at="",
            )
    except Exception as e:
        logger.exception(
            f"Failed to resume Stripe subscription for policy {policy.pk}: {e}"
        )
        return 400, {
            "success": False,
            "message": f"Unable to resume subscription: {e}",
            "data": None,
        }

    policy.status = "active"
    policy.save(update_fields=["status"])
    logger.info(
        f"Policy {policy.policy_number} reinstated by user {request.auth.email}"
    )

    return 200, {
        "success": True,
        "message": "Policy reinstated successfully",
        "data": {
            "policy_id": policy.pk,
            "policy_number": policy.policy_number,
            "status": policy.status,
        },
    }


# ── Coverage Modification Requests (V3 #9) ────────────────────────────────────


class CoverageModificationRequestSchema(Schema):
    requested_changes: dict
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()


@router.post(
    "/{policy_id}/modify-coverage",
    auth=JWTAuth(),
    response={
        201: ApiResponseSchema,
        404: ApiResponseSchema,
        403: ApiResponseSchema,
        400: ApiResponseSchema,
    },
)
def request_coverage_modification(
    request: HttpRequest,
    policy_id: int,
    payload: CoverageModificationRequestSchema,
) -> tuple[int, dict[str, Any]]:
    """Submit a coverage modification request for an existing policy.

    The request is placed in 'pending' status. A Corgi underwriter will
    review and approve or deny via Django admin.

    Args:
        request: HTTP request with JWT-authenticated user.
        policy_id: Primary key of the policy to modify.
        payload: JSON body with requested_changes (dict) and reason (str).

    Returns:
        201 on success, 404 if policy not found, 403 if not authorized, 400 on validation error.
    """
    from organizations.service import OrganizationService

    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if policy.status in ("cancelled", "expired"):
        return 400, {
            "success": False,
            "message": f"Cannot modify a {policy.status} policy",
            "data": None,
        }

    mod_request = CoverageModificationRequest.objects.create(
        policy=policy,
        requested_changes=payload.requested_changes,
        reason=payload.reason,
        status="pending",
        requested_by=request.auth,
    )

    return 201, {
        "success": True,
        "message": "Coverage modification request submitted successfully. An underwriter will review shortly.",
        "data": {
            "request_id": mod_request.pk,
            "status": mod_request.status,
            "policy_number": policy.policy_number,
        },
    }


# ── Activity Log (V3 #13) ─────────────────────────────────────────────────────


@router.get(
    "/activity-log",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Activity log for the policyholder's organization",
)
def get_activity_log(
    request: HttpRequest,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, dict[str, Any]]:
    """Return a timeline of all activity events for the current organization.

    Aggregates:
    - Policy creation, modification, and cancellation events
    - Payment events (successful payments, refunds)
    - Coverage modification requests
    - Certificate requests
    - Member invite / join events

    Returns events sorted by timestamp descending, with actor info,
    event type, description, and metadata.
    """
    from organizations.service import OrganizationService
    from policies.models import Policy, Payment, CoverageModificationRequest
    from certificates.models import CustomCertificate
    from organizations.models import OrganizationMember

    org_id = OrganizationService.get_active_org_id(request.auth)
    events = []

    # ── Policy events ──
    policies_qs = (
        Policy.objects.filter(
            quote__organization_id=org_id,
            is_deleted=False,
        )
        .select_related("quote__company", "quote__organization")
        .order_by("-created_at")[:200]
    )

    for p in policies_qs:
        actor_email = (
            p.quote.organization.members.filter(role="owner")
            .values_list("user__email", flat=True)
            .first()
            or "System"
        )
        events.append(
            {
                "id": f"policy-{p.pk}-created",
                "type": "policy_created",
                "title": "Policy bound",
                "description": f"{p.coverage_type.replace('-', ' ').title()} policy #{p.policy_number} was activated",
                "actor": actor_email,
                "metadata": {
                    "policy_number": p.policy_number,
                    "coverage_type": p.coverage_type,
                    "premium": str(p.premium),
                },
                "timestamp": p.created_at.isoformat(),
            }
        )

        if p.status in ("cancelled", "expired"):
            events.append(
                {
                    "id": f"policy-{p.pk}-status",
                    "type": "policy_status_changed",
                    "title": f"Policy {p.status}",
                    "description": f"Policy #{p.policy_number} is now {p.status}",
                    "actor": "System",
                    "metadata": {
                        "policy_number": p.policy_number,
                        "status": p.status,
                    },
                    "timestamp": p.updated_at.isoformat(),
                }
            )

    # ── Payment events ──
    payments_qs = (
        Payment.objects.filter(
            policy__quote__organization_id=org_id,
        )
        .select_related("policy")
        .order_by("-paid_at")[:100]
    )

    for pay in payments_qs:
        events.append(
            {
                "id": f"payment-{pay.pk}",
                "type": "payment_received",
                "title": "Payment received",
                "description": f"Payment of ${pay.amount} received for policy #{pay.policy.policy_number}",
                "actor": "Stripe",
                "metadata": {
                    "amount": str(pay.amount),
                    "policy_number": pay.policy.policy_number,
                    "stripe_invoice_id": pay.stripe_invoice_id,
                    "payment_method": pay.payment_method,
                },
                "timestamp": pay.paid_at.isoformat(),
            }
        )

        if pay.refund_amount:
            events.append(
                {
                    "id": f"refund-{pay.pk}",
                    "type": "payment_refunded",
                    "title": "Refund issued",
                    "description": f"Refund of ${pay.refund_amount} issued for policy #{pay.policy.policy_number}",
                    "actor": "System",
                    "metadata": {
                        "amount": str(pay.refund_amount),
                        "reason": pay.refund_reason,
                        "policy_number": pay.policy.policy_number,
                    },
                    "timestamp": pay.refunded_at.isoformat()
                    if pay.refunded_at
                    else pay.updated_at.isoformat(),
                }
            )

    # ── Coverage modification requests ──
    mod_requests_qs = (
        CoverageModificationRequest.objects.filter(
            policy__quote__organization_id=org_id,
        )
        .select_related("policy", "requested_by")
        .order_by("-created_at")[:50]
    )

    for mr in mod_requests_qs:
        actor = mr.requested_by.email if mr.requested_by else "Unknown"
        events.append(
            {
                "id": f"mod-request-{mr.pk}",
                "type": "coverage_modification_requested",
                "title": "Coverage modification requested",
                "description": f"{actor} requested a coverage change on policy #{mr.policy.policy_number}",
                "actor": actor,
                "metadata": {
                    "policy_number": mr.policy.policy_number,
                    "status": mr.status,
                    "reason": mr.reason,
                },
                "timestamp": mr.created_at.isoformat(),
            }
        )

    # ── Certificate requests ──
    try:
        certs_qs = (
            CustomCertificate.objects.filter(
                policy__quote__organization_id=org_id,
            )
            .select_related("policy")
            .order_by("-created_at")[:50]
        )

        for cert in certs_qs:
            events.append(
                {
                    "id": f"cert-{cert.pk}",
                    "type": "certificate_requested",
                    "title": "Certificate of Insurance issued",
                    "description": f"COI issued for policy #{cert.policy.policy_number}",
                    "actor": "Portal",
                    "metadata": {
                        "policy_number": cert.policy.policy_number,
                        "holder_name": getattr(cert, "holder_name", None),
                    },
                    "timestamp": cert.created_at.isoformat(),
                }
            )
    except Exception:
        pass  # Certificates may not always be accessible

    # ── Org member joins ──
    members_qs = (
        OrganizationMember.objects.filter(
            organization_id=org_id,
        )
        .select_related("user")
        .order_by("-created_at")[:20]
    )

    for member in members_qs:
        events.append(
            {
                "id": f"member-{member.pk}",
                "type": "member_joined",
                "title": "Team member joined",
                "description": f"{member.user.email} joined the organization as {member.role}",
                "actor": member.user.email,
                "metadata": {
                    "email": member.user.email,
                    "role": member.role,
                },
                "timestamp": member.created_at.isoformat(),
            }
        )

    # Sort all events by timestamp descending
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    total = len(events)
    paginated = events[offset : offset + limit]

    return 200, {
        "success": True,
        "message": "Activity log retrieved successfully",
        "data": {
            "events": paginated,
            "total": total,
            "limit": limit,
            "offset": offset,
        },
    }


# ── Policy Cancellation (V3 #5.1 — Self-serve cancel flow) ───────────────────


class PolicyCancelSchema(Schema):
    effective_date: str  # YYYY-MM-DD
    reason: str
    reason_text: str = ""

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()


@router.post(
    "/{policy_id}/cancel",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
        404: ApiResponseSchema,
    },
    summary="Submit a self-serve cancellation request (multi-step)",
)
def cancel_policy(
    request: HttpRequest,
    policy_id: int,
    payload: PolicyCancelSchema,
) -> tuple[int, dict[str, Any]]:
    """Cancel a policy at a future effective date.

    Schedules the Stripe subscription to cancel at the effective date and
    marks the policy as ``pending_cancellation``. A confirmation email is
    sent via EmailService. The policy only transitions to ``cancelled``
    when the ``customer.subscription.deleted`` webhook fires.

    Body:
        effective_date: YYYY-MM-DD (must be today or later, not past expiration)
        reason: Short reason code (e.g. ``too_expensive``)
        reason_text: Optional free-text explanation.

    Returns:
        200 on success, 400 on validation error, 403 if not authorized,
        404 if the policy isn't found.
    """
    import datetime
    import logging
    from django.conf import settings
    from django.template.loader import render_to_string
    from django.utils import timezone
    from organizations.service import OrganizationService
    from stripe_integration.service import StripeService
    from emails.service import EmailService
    from emails.schemas import SendEmailInput

    logger = logging.getLogger(__name__)

    # ── Lookup + auth ───────────────────────────────────────────────
    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.select_related(
            "quote__company", "quote__user", "quote__organization"
        ).get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if policy.status in ("cancelled", "expired", "pending_cancellation"):
        return 400, {
            "success": False,
            "message": f"Policy is already {policy.get_status_display().lower()}.",
            "data": None,
        }

    # ── Validate effective_date ─────────────────────────────────────
    try:
        effective_date = datetime.date.fromisoformat(payload.effective_date)
    except ValueError:
        return 400, {
            "success": False,
            "message": "Invalid date format. Use YYYY-MM-DD.",
            "data": None,
        }

    today = datetime.date.today()
    if effective_date < today:
        return 400, {
            "success": False,
            "message": "Effective date cannot be in the past.",
            "data": None,
        }
    if policy.expiration_date and effective_date > policy.expiration_date:
        return 400, {
            "success": False,
            "message": "Effective date cannot be later than the policy expiration date.",
            "data": None,
        }

    # ── Stripe: schedule cancel_at on the subscription ──────────────
    if policy.stripe_subscription_id:
        try:
            client = StripeService.get_client()
            cancel_at_ts = int(
                datetime.datetime.combine(
                    effective_date, datetime.time.min, tzinfo=datetime.timezone.utc
                ).timestamp()
            )
            client.Subscription.modify(
                policy.stripe_subscription_id,
                cancel_at=cancel_at_ts,
                metadata={
                    "cancel_reason": payload.reason,
                    "cancel_reason_text": payload.reason_text or "",
                    "cancel_requested_by": request.auth.email,
                    "cancel_requested_at": timezone.now().isoformat(),
                },
            )
        except Exception as e:
            logger.exception(
                "Failed to schedule Stripe cancellation for policy %s: %s",
                policy.policy_number,
                e,
            )
            return 400, {
                "success": False,
                "message": "Unable to schedule cancellation with the payment processor. "
                "Please try again or contact support.",
                "data": None,
            }

    # ── Mark policy as pending_cancellation ─────────────────────────
    # NOTE: we do NOT set status='cancelled' immediately — the
    # customer.subscription.deleted webhook finalises that transition.
    policy.status = "pending_cancellation"
    policy.save(update_fields=["status", "updated_at"], skip_validation=True)

    # ── Record a cancellation note on the policy (best effort) ──────
    try:
        CoverageModificationRequest.objects.create(
            policy=policy,
            requested_changes={
                "action": "cancel",
                "effective_date": effective_date.isoformat(),
                "reason_code": payload.reason,
            },
            reason=(payload.reason_text or payload.reason)[:2000],
            status="approved",  # Customer-initiated self-serve, auto-approved
            requested_by=request.auth,
        )
    except Exception:
        logger.warning(
            "Failed to record cancellation note for policy %s",
            policy.policy_number,
            exc_info=True,
        )

    # ── Fire confirmation email ─────────────────────────────────────
    try:
        user = policy.quote.user
        company_name = (
            policy.quote.company.entity_legal_name if policy.quote.company else ""
        )
        html = render_to_string(
            "emails/policy_cancelled.html",
            {
                "contact_name": user.get_full_name() or user.email,
                "company_name": company_name,
                "policy_numbers": policy.policy_number,
                "coverages": [policy.coverage_type],
                "effective_date": effective_date,
                "expiration_date": policy.expiration_date,
            },
        )
        EmailService.send(
            SendEmailInput(
                to=[user.email],
                subject=f"Cancellation scheduled: policy {policy.policy_number}",
                html=html,
                from_email=settings.HELLO_CORGI_EMAIL,
            )
        )
    except Exception as e:
        logger.exception(
            "Failed to send cancellation confirmation email for policy %s: %s",
            policy.policy_number,
            e,
        )

    return 200, {
        "success": True,
        "message": "Cancellation scheduled. A confirmation email is on its way.",
        "data": {
            "policy_id": policy.pk,
            "policy_number": policy.policy_number,
            "status": policy.status,
            "effective_date": effective_date.isoformat(),
            "reason": payload.reason,
        },
    }


# ── Annual Review Scheduler (V3 #16) ─────────────────────────────────────────


class ScheduleReviewSchema(Schema):
    preferred_date: str  # YYYY-MM-DD
    preferred_time: str = ""  # HH:MM
    timezone: str = "America/New_York"
    topics: list[str] = []
    notes: str = ""


@router.post(
    "/schedule-review",
    auth=JWTAuth(),
    response={201: ApiResponseSchema, 400: ApiResponseSchema},
    summary="Schedule an annual coverage review call",
)
def schedule_review(
    request: HttpRequest,
    payload: ScheduleReviewSchema,
) -> tuple[int, dict[str, Any]]:
    """Schedule an annual coverage review call with the customer's AE.

    Stores a ReviewSchedule record and triggers an internal notification
    (Slack webhook if configured) so the AE is alerted.

    Args:
        payload.preferred_date: Preferred date in YYYY-MM-DD format
        payload.preferred_time: Preferred time in HH:MM format
        payload.timezone: Customer's timezone
        payload.topics: List of topics to discuss
        payload.notes: Additional context

    Returns:
        201 with review schedule details.
    """
    import datetime
    from organizations.service import OrganizationService

    # Validate date
    try:
        preferred_date = datetime.date.fromisoformat(payload.preferred_date)
        if preferred_date < datetime.date.today():
            return 400, {
                "success": False,
                "message": "Preferred date must be in the future",
                "data": None,
            }
    except ValueError:
        return 400, {
            "success": False,
            "message": "Invalid date format. Use YYYY-MM-DD",
            "data": None,
        }

    org_id = OrganizationService.get_active_org_id(request.auth)

    review = ReviewSchedule.objects.create(
        organization_id=org_id,
        requested_by=request.auth,
        preferred_date=preferred_date,
        preferred_time=payload.preferred_time,
        timezone=payload.timezone,
        topics=", ".join(payload.topics) if payload.topics else "",
        notes=payload.notes,
        status="pending",
    )

    # Notify via Slack webhook if configured
    try:
        import os
        import json as _json
        import urllib.request

        slack_url = os.getenv("SLACK_WEBHOOK_URL")
        if slack_url:
            topics_text = (
                ", ".join(payload.topics) if payload.topics else "Not specified"
            )
            data = _json.dumps(
                {
                    "text": "📅 New Coverage Review Scheduled",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": "📅 Annual Coverage Review Request",
                            },
                        },
                        {
                            "type": "section",
                            "fields": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Customer:*\n{request.auth.email}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Preferred Date:*\n{payload.preferred_date}",
                                },
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Preferred Time:*\n{payload.preferred_time or 'Flexible'} ({payload.timezone})",
                                },
                                {"type": "mrkdwn", "text": f"*Topics:*\n{topics_text}"},
                            ],
                        },
                        *(
                            [
                                {
                                    "type": "section",
                                    "text": {
                                        "type": "mrkdwn",
                                        "text": f"*Notes:*\n{payload.notes}",
                                    },
                                }
                            ]
                            if payload.notes
                            else []
                        ),
                    ],
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                slack_url,
                data=data,
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass  # Slack notification is best-effort

    return 201, {
        "success": True,
        "message": "Review scheduled successfully! Your account executive will be in touch to confirm.",
        "data": {
            "id": review.pk,
            "preferred_date": review.preferred_date.isoformat(),
            "preferred_time": review.preferred_time,
            "timezone": review.timezone,
            "topics": review.topics,
            "status": review.status,
        },
    }


# ── Pay-as-You-Go Endorsement Invoice (H7) ───────────────────────────────────


class EndorsementInvoiceSchema(Schema):
    """Request body for POST /policies/{id}/endorsement-invoice.

    Used to generate a Stripe `send_invoice` payment link for a midterm
    limit increase when the customer has no card on file. The endorsement
    itself is only applied once Stripe confirms the invoice has been paid.
    """

    coverage: str
    new_limit: int
    reason: str

    @field_validator("reason")
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()

    @field_validator("new_limit")
    @classmethod
    def new_limit_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("new_limit must be a positive integer")
        return v


@router.post(
    "/{policy_id}/endorsement-invoice",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
        404: ApiResponseSchema,
    },
    summary="Generate a pay-as-you-go Stripe invoice for a limit-increase endorsement",
)
def create_endorsement_invoice(
    request: HttpRequest,
    policy_id: int,
    payload: EndorsementInvoiceSchema,
) -> tuple[int, dict[str, Any]]:
    """Create a Stripe `send_invoice` for a midterm limit increase.

    When a customer has no saved payment method, off-session charges fail —
    so endorsements that increase exposure cannot be applied inline. This
    endpoint produces a hosted Stripe invoice the customer can pay at their
    leisure; once Stripe fires ``invoice.paid`` the webhook applies the
    endorsement (via the existing :meth:`PolicyService.endorse_modify_limits`
    flow) and regenerates the COI documents.

    Body:
        coverage: Coverage slug (e.g. ``cyber-liability``) — must match the
            policy's ``coverage_type``.
        new_limit: Requested new aggregate limit in dollars.
        reason: Free-text rationale (shown on the invoice / audit trail).

    Returns:
        200 with ``{invoice_id, hosted_invoice_url}``.
        400 if the new limit is not an increase, the policy has no Stripe
        customer, or the rating service cannot produce a premium for the
        new limit.
    """
    import logging
    from decimal import Decimal

    from django.conf import settings
    from django.template.loader import render_to_string

    from organizations.service import OrganizationService
    from emails.service import EmailService
    from emails.schemas import SendEmailInput
    from rating.rules import get_definition
    from rating.service import RatingService
    from stripe_integration.invoices import create_pay_as_you_go_invoice

    logger = logging.getLogger(__name__)

    # ── Lookup + auth ───────────────────────────────────────────────
    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.select_related("quote__user", "quote__company").get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if policy.coverage_type != payload.coverage:
        return 400, {
            "success": False,
            "message": (
                f"Coverage mismatch: policy is {policy.coverage_type!r}, payload requested {payload.coverage!r}"
            ),
            "data": None,
        }

    if policy.status != "active":
        return 400, {
            "success": False,
            "message": f"Cannot endorse a {policy.status} policy",
            "data": None,
        }

    if policy.is_brokered:
        return 400, {
            "success": False,
            "message": "Brokered policies cannot be endorsed via pay-as-you-go invoice",
            "data": None,
        }

    if not policy.stripe_customer_id:
        return 400, {
            "success": False,
            "message": "Policy has no Stripe customer on file",
            "data": None,
        }

    # ── Premium delta via RatingService ─────────────────────────────
    # Re-rate the policy at the new aggregate limit and diff against the
    # current full-term premium. Uses the coverage definition's limit
    # factor curve by applying the ratio (new_limit_factor / current_limit_factor)
    # to the stored full-term premium.
    definition = get_definition(policy.coverage_type)
    if definition is None:
        return 400, {
            "success": False,
            "message": f"No rating definition for coverage {policy.coverage_type}",
            "data": None,
        }

    current_limits = policy.limits_retentions or {}
    current_limit = int(current_limits.get("aggregate_limit") or 0)
    if current_limit <= 0:
        return 400, {
            "success": False,
            "message": "Policy has no current aggregate limit recorded",
            "data": None,
        }

    if payload.new_limit <= current_limit:
        return 400, {
            "success": False,
            "message": (
                f"new_limit ({payload.new_limit:,}) must be greater than the current limit ({current_limit:,})"
            ),
            "data": None,
        }

    old_factor = RatingService._get_limit_factor(definition, current_limit)
    new_factor = RatingService._get_limit_factor(definition, payload.new_limit)
    if not old_factor or old_factor <= 0:
        return 400, {
            "success": False,
            "message": "Unable to determine current rating factor for policy",
            "data": None,
        }

    factor_ratio = Decimal(str(new_factor)) / Decimal(str(old_factor))
    new_premium = (Decimal(str(policy.premium)) * factor_ratio).quantize(
        Decimal("0.01")
    )
    full_term_delta = new_premium - Decimal(str(policy.premium))

    if full_term_delta <= 0:
        return 400, {
            "success": False,
            "message": (
                f"Computed premium delta is not positive (old=${policy.premium}, "
                f"new=${new_premium}); nothing to invoice"
            ),
            "data": None,
        }

    # Prorate to the remaining policy term so the customer isn't charged
    # for coverage they've already consumed.
    from policies.service import PolicyService  # local import to avoid cycle

    proration_factor = PolicyService._calculate_proration_factor(policy)
    prorated_delta = (full_term_delta * proration_factor).quantize(Decimal("0.01"))
    if prorated_delta <= 0:
        return 400, {
            "success": False,
            "message": "Prorated premium delta is zero — policy may be at expiration",
            "data": None,
        }

    amount_cents = int(round(float(prorated_delta) * 100))

    # ── Invoice metadata contract ───────────────────────────────────
    # The webhook handler branches on `metadata['type'] == 'endorsement'`.
    invoice_metadata = {
        "type": "endorsement",
        "policy_id": str(policy.pk),
        "policy_number": policy.policy_number,
        "coverage": policy.coverage_type,
        "current_limit": str(current_limit),
        "new_limit": str(payload.new_limit),
        "new_premium": str(new_premium),
        "old_premium": str(policy.premium),
        "prorated_delta": str(prorated_delta),
        "reason": payload.reason[:200],
        "requested_by": request.auth.email,
    }

    description = (
        f"Endorsement: increase {policy.coverage_type} limit on "
        f"{policy.policy_number} from ${current_limit:,} to "
        f"${payload.new_limit:,} (prorated)"
    )

    try:
        invoice = create_pay_as_you_go_invoice(
            customer_id=policy.stripe_customer_id,
            line_items=[
                {
                    "amount_cents": amount_cents,
                    "description": description,
                    "metadata": {
                        "policy_id": str(policy.pk),
                        "coverage": policy.coverage_type,
                    },
                }
            ],
            metadata=invoice_metadata,
            due_days=14,
        )
    except Exception as e:
        logger.exception(
            "Failed to create pay-as-you-go invoice for policy %s: %s",
            policy.policy_number,
            e,
        )
        return 400, {
            "success": False,
            "message": f"Unable to create invoice: {e}",
            "data": None,
        }

    hosted_url = getattr(invoice, "hosted_invoice_url", None) or ""

    # ── Send payment-link email (reuses payment_reminder template) ──
    try:
        user = policy.quote.user
        EmailService.send(
            SendEmailInput(
                to=[user.email],
                subject=f"Payment link: endorsement for policy {policy.policy_number}",
                html=render_to_string(
                    "emails/payment_reminder.html",
                    {
                        "first_name": user.first_name
                        or user.get_full_name()
                        or "there",
                        "amount": f"{prorated_delta:,.2f}",
                        "policy_number": policy.policy_number,
                        "due_date": f"{14} days from now",
                        "portal_url": hosted_url or settings.PORTAL_BASE_URL,
                    },
                ),
                from_email=settings.HELLO_CORGI_EMAIL,
            )
        )
    except Exception as e:
        logger.exception(
            "Failed to send endorsement payment-link email for policy %s: %s",
            policy.policy_number,
            e,
        )

    return 200, {
        "success": True,
        "message": "Endorsement invoice created",
        "data": {
            "invoice_id": invoice.id,
            "hosted_invoice_url": hosted_url,
            "amount": str(prorated_delta),
            "new_limit": payload.new_limit,
        },
    }


@router.get(
    "/schedule-review",
    auth=JWTAuth(),
    response={200: ApiResponseSchema},
    summary="Get pending review schedules for the current org",
)
def get_review_schedules(
    request: HttpRequest,
) -> tuple[int, dict[str, Any]]:
    """List review schedules for the current organization."""
    from organizations.service import OrganizationService

    org_id = OrganizationService.get_active_org_id(request.auth)
    schedules = ReviewSchedule.objects.filter(
        organization_id=org_id,
    ).order_by("-created_at")

    return 200, {
        "success": True,
        "message": "Review schedules retrieved",
        "data": [
            {
                "id": s.pk,
                "preferred_date": s.preferred_date.isoformat(),
                "preferred_time": s.preferred_time,
                "timezone": s.timezone,
                "topics": s.topics,
                "notes": s.notes,
                "status": s.status,
                "confirmed_datetime": s.confirmed_datetime.isoformat()
                if s.confirmed_datetime
                else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in schedules
        ],
    }


# ── Self-Serve Raise Limit (6.4) ─────────────────────────────────────────────


class RaiseLimitSchema(Schema):
    """Request body for POST /policies/{id}/raise-limit.

    Used by the self-serve portal page to bump an aggregate limit up to
    ``MAX_SELF_SERVE_LIMIT`` without staff involvement.
    """

    coverage: str
    new_limit: int

    @field_validator("new_limit")
    @classmethod
    def new_limit_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("new_limit must be a positive integer")
        return v


@router.post(
    "/{policy_id}/raise-limit",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
        404: ApiResponseSchema,
    },
    summary="Self-serve raise of an aggregate coverage limit",
)
def raise_coverage_limit(
    request: HttpRequest,
    policy_id: int,
    payload: RaiseLimitSchema,
) -> tuple[int, dict[str, Any]]:
    """Raise a policy's aggregate limit up to ``MAX_SELF_SERVE_LIMIT``.

    Re-rates the policy at the new limit using the coverage's rating
    factor curve, then reuses :meth:`PolicyService.endorse_modify_limits`
    to apply the endorsement inline (prorated charge, new COI).
    """
    from decimal import Decimal

    from organizations.service import OrganizationService
    from rating.rules import get_definition
    from rating.service import RatingService
    from common.constants import MAX_SELF_SERVE_LIMIT

    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.select_related("quote__user", "quote__company").get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if policy.coverage_type != payload.coverage:
        return 400, {
            "success": False,
            "message": (
                f"Coverage mismatch: policy is {policy.coverage_type!r}, payload requested {payload.coverage!r}"
            ),
            "data": None,
        }

    current_limits = policy.limits_retentions or {}
    current_limit = int(current_limits.get("aggregate_limit") or 0)
    if current_limit <= 0:
        return 400, {
            "success": False,
            "message": "Policy has no current aggregate limit recorded",
            "data": None,
        }

    if payload.new_limit <= current_limit:
        return 400, {
            "success": False,
            "message": (
                f"new_limit ({payload.new_limit:,}) must be greater than the current limit ({current_limit:,})"
            ),
            "data": None,
        }

    if payload.new_limit > MAX_SELF_SERVE_LIMIT:
        return 400, {
            "success": False,
            "message": (
                f"new_limit ({payload.new_limit:,}) exceeds the self-serve "
                f"maximum of ${MAX_SELF_SERVE_LIMIT:,}. Contact your broker."
            ),
            "data": None,
        }

    definition = get_definition(policy.coverage_type)
    if definition is None:
        return 400, {
            "success": False,
            "message": f"No rating definition for coverage {policy.coverage_type}",
            "data": None,
        }

    old_factor = RatingService._get_limit_factor(definition, current_limit)
    new_factor = RatingService._get_limit_factor(definition, payload.new_limit)
    if not old_factor or old_factor <= 0:
        return 400, {
            "success": False,
            "message": "Unable to determine current rating factor for policy",
            "data": None,
        }

    factor_ratio = Decimal(str(new_factor)) / Decimal(str(old_factor))
    new_premium = (Decimal(str(policy.premium)) * factor_ratio).quantize(
        Decimal("0.01")
    )

    new_limits = dict(current_limits)
    new_limits["aggregate_limit"] = payload.new_limit

    try:
        result = PolicyService.endorse_modify_limits(
            policy=policy,
            new_limits=new_limits,
            new_premium=new_premium,
            admin_reason=f"Self-serve limit raise to ${payload.new_limit:,}",
        )
    except ValueError as e:
        return 400, {"success": False, "message": str(e), "data": None}

    return 200, {
        "success": True,
        "message": "Limit raised successfully",
        "data": {
            "policy_id": policy.pk,
            "coverage": policy.coverage_type,
            "new_limit": payload.new_limit,
            "new_premium": str(new_premium),
            "result": result,
        },
    }


@router.patch(
    "/{policy_id}",
    auth=JWTAuth(),
    response={
        200: ApiResponseSchema,
        400: ApiResponseSchema,
        403: ApiResponseSchema,
        404: ApiResponseSchema,
    },
    summary="Self-serve edit of policy mailing address / named-insured company name",
)
def edit_policy(
    request: HttpRequest,
    policy_id: int,
    payload: PolicyEditSchema,
) -> tuple[int, dict[str, Any]]:
    """Update the mailing address and/or company (named insured) legal name on a policy.

    The payload is strictly allowlisted — only ``address`` and
    ``company_name`` are persisted; anything else is ignored. Ownership is
    enforced via ``quote__organization_id``, so callers must be a member of
    the organization that owns the policy.

    After a successful mutation we fire-and-forget a regeneration of the
    main policy document via
    :func:`documents_generator.service.DocumentsGeneratorService.regenerate_policy_doc_with_endorsement`,
    which builds a Named-Insured-change endorsement PDF, merges it onto the
    most recent main policy doc, uploads the result to S3, and versions it
    as a new ``UserDocument``. Failures there are swallowed — document
    regeneration must never block the mutation.
    """
    import logging
    from organizations.service import OrganizationService

    logger = logging.getLogger(__name__)

    # ── Lookup + ownership check ──────────────────────────────────────
    try:
        org_id = OrganizationService.get_active_org_id(request.auth)
        policy = Policy.objects.select_related(
            "quote__company__business_address",
            "quote__organization",
        ).get(
            pk=policy_id,
            quote__organization_id=org_id,
            is_deleted=False,
        )
    except Policy.DoesNotExist:
        return 404, {"success": False, "message": "Policy not found", "data": None}

    if payload.address is None and payload.company_name is None:
        return 400, {
            "success": False,
            "message": "Provide at least one of address or company_name.",
            "data": None,
        }

    # ── Apply the allowlisted fields ──────────────────────────────────
    # 1) mailing_address lives on Policy as a JSON blob
    before_company_name = policy.insured_legal_name or (
        policy.quote.company.entity_legal_name
        if policy.quote and policy.quote.company
        else ""
    )
    before_address = policy.mailing_address or {}

    if payload.address is not None:
        policy.mailing_address = {
            "street": payload.address.street,
            "suite": payload.address.suite,
            "city": payload.address.city,
            "state": payload.address.state,
            "zip": payload.address.zip,
        }
        policy.principal_state = payload.address.state

    if payload.company_name is not None:
        policy.insured_legal_name = payload.company_name

    policy.save(
        update_fields=[
            "mailing_address",
            "principal_state",
            "insured_legal_name",
            "updated_at",
        ],
        skip_validation=True,
    )

    # ── Mirror company.entity_legal_name & business_address on the Quote.company ──
    # The COI + policy docs pull the named insured from ``quote.company``, so
    # we keep that row in sync for future document regeneration.
    try:
        company = policy.quote.company
        if company is not None:
            company_fields = []
            if payload.company_name is not None:
                company.entity_legal_name = payload.company_name
                company_fields.append("entity_legal_name")
            if company_fields:
                company.save(update_fields=company_fields)

            if payload.address is not None and company.business_address is not None:
                addr = company.business_address
                addr.street_address = payload.address.street
                addr.suite = payload.address.suite
                addr.city = payload.address.city
                addr.state = payload.address.state
                addr.zip = payload.address.zip
                addr.save(
                    update_fields=[
                        "street_address",
                        "suite",
                        "city",
                        "state",
                        "zip",
                        "updated_at",
                    ]
                )
    except Exception:
        logger.warning(
            "Failed to mirror address/company name onto quote.company for policy %s",
            policy.policy_number,
            exc_info=True,
        )

    # ── Fire-and-forget: regenerate policy PDF with a name-change endorsement. ─
    # We reuse DocumentsGeneratorService.regenerate_policy_doc_with_endorsement
    # by wrapping the edit as a lightweight AdditionalInsured-shaped payload.
    # Any failure is logged but never raised — document regeneration must not
    # block the underlying edit.
    regen_result = None
    try:
        from documents_generator.service import DocumentsGeneratorService

        after_company_name = policy.insured_legal_name or before_company_name
        after_address = policy.mailing_address or before_address
        address_line = ""
        if after_address:
            parts = [
                after_address.get("street", ""),
                after_address.get("suite", ""),
                after_address.get("city", ""),
                after_address.get("state", ""),
                after_address.get("zip", ""),
            ]
            address_line = ", ".join(p for p in parts if p)

        class _EditShim:
            """Duck-typed stand-in for AdditionalInsured used by the regen helper.

            The helper only reads ``name``, ``address``, ``created_by``,
            ``organization`` and ``pk`` off this object, so a simple shim is
            enough to re-use the existing regeneration + S3 upload pipeline."""

            def __init__(
                self, name: str, address: str, created_by, organization, pk: int
            ):
                self.name = name
                self.address = address
                self.created_by = created_by
                self.organization = organization
                self.pk = pk

        shim = _EditShim(
            name=after_company_name or "—",
            address=address_line,
            created_by=request.auth,
            organization=policy.quote.organization if policy.quote else None,
            pk=policy.pk,
        )

        regen_result = DocumentsGeneratorService.regenerate_policy_doc_with_endorsement(
            policy=policy,
            additional_insured=shim,
            user=request.auth,
            organization=policy.quote.organization if policy.quote else None,
        )
    except Exception:
        logger.exception(
            "Policy doc regeneration failed for policy %s after address/name edit",
            policy.policy_number,
        )

    return 200, {
        "success": True,
        "message": "Policy updated successfully",
        "data": {
            "policy_id": policy.pk,
            "policy_number": policy.policy_number,
            "mailing_address": policy.mailing_address,
            "company_name": policy.insured_legal_name,
            "document_regenerated": bool(regen_result),
        },
    }
