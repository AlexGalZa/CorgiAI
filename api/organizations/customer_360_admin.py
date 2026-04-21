"""
Customer 360 View — Django admin page.

Shows a unified timeline for a single organization:
- All quotes
- All policies
- All claims
- All payments
- All certificates
- All communications (dunning records, notifications)

Accessible at: /admin/organizations/<org_id>/360/
"""

import logging

from django.contrib import admin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from organizations.models import Organization

logger = logging.getLogger(__name__)


def customer_360_view(request, org_id: int):
    """Render the Customer 360 view for an organization."""
    if not request.user.is_staff:
        return HttpResponseForbidden("Staff access required.")

    org = get_object_or_404(Organization, pk=org_id)

    # ── Gather all data ──────────────────────────────────────────────────────

    # Quotes
    from quotes.models import Quote

    quotes = list(
        Quote.objects.filter(organization=org)
        .select_related("company", "company__business_address", "user")
        .order_by("-created_at")
    )

    # Policies
    from policies.models import Policy, Payment

    policies = list(
        Policy.objects.filter(quote__organization=org)
        .select_related("quote__company")
        .order_by("-created_at")
    )

    policy_ids = [p.id for p in policies]

    # Payments
    payments = list(Payment.objects.filter(policy__in=policy_ids).order_by("-paid_at"))

    # Claims
    from claims.models import Claim

    claims = list(
        Claim.objects.filter(policy__in=policy_ids)
        .select_related("policy")
        .order_by("-created_at")
    )

    # Certificates
    from certificates.models import CustomCertificate

    certificates = list(
        CustomCertificate.objects.filter(policy__in=policy_ids)
        .select_related("policy")
        .order_by("-created_at")
    )

    # Dunning records
    from stripe_integration.models import DunningRecord

    dunning_records = list(
        DunningRecord.objects.filter(policy__in=policy_ids)
        .select_related("policy")
        .order_by("-created_at")
    )

    # Notifications (audit log of key events)
    try:
        from common.models import Notification

        # Get notifications related to any of the org's policies, quotes, or users
        owner = org.owner
        notifications = list(
            Notification.objects.filter(user=owner).order_by("-created_at")[:50]
        )
    except Exception:
        notifications = []

    # Members
    members = list(org.members.select_related("user").order_by("role", "created_at"))

    # ── Build unified timeline ───────────────────────────────────────────────
    timeline = _build_timeline(
        quotes, policies, payments, claims, certificates, dunning_records, notifications
    )

    # ── Stats ────────────────────────────────────────────────────────────────
    from decimal import Decimal

    total_premium = sum(p.premium or Decimal("0") for p in policies)
    total_paid = sum(
        pay.amount or Decimal("0") for pay in payments if pay.status == "paid"
    )
    active_policies_count = sum(1 for p in policies if p.status == "active")
    open_claims_count = sum(1 for c in claims if c.status not in ("closed", "denied"))

    stats = {
        "total_quotes": len(quotes),
        "total_policies": len(policies),
        "active_policies": active_policies_count,
        "total_claims": len(claims),
        "open_claims": open_claims_count,
        "total_payments": len(payments),
        "total_certificates": len(certificates),
        "total_premium": float(total_premium),
        "total_paid": float(total_paid),
    }

    context = {
        **admin.site.each_context(request),
        "title": f"Customer 360 — {org.name}",
        "org": org,
        "members": members,
        "quotes": quotes,
        "policies": policies,
        "payments": payments[:25],  # Show most recent 25
        "claims": claims,
        "certificates": certificates,
        "dunning_records": dunning_records,
        "notifications": notifications[:20],
        "timeline": timeline[:60],  # Show most recent 60 events
        "stats": stats,
        "opts": {"app_label": "organizations", "model_name": "organization"},
    }
    return render(request, "admin/organizations/customer_360.html", context)


def _build_timeline(
    quotes, policies, payments, claims, certificates, dunning_records, notifications
) -> list[dict]:
    """
    Merge all events into a unified timeline sorted by date (newest first).
    Each event is a dict with: type, title, description, date, url, color.
    """
    from django.urls import reverse

    events = []

    for q in quotes:
        try:
            url = reverse("admin:quotes_quote_change", args=[q.pk])
        except Exception:
            url = "#"
        status_colors = {
            "needs_review": "#f59e0b",
            "quoted": "#3b82f6",
            "purchased": "#10b981",
            "declined": "#ef4444",
            "draft": "#9ca3af",
            "submitted": "#6366f1",
        }
        events.append(
            {
                "type": "quote",
                "icon": "📋",
                "title": f"Quote {q.quote_number}",
                "description": (
                    f"{', '.join(c.replace('-', ' ').title() for c in (q.coverages or [])[:3])}"
                    + (
                        f" (+{len(q.coverages) - 3} more)"
                        if len(q.coverages or []) > 3
                        else ""
                    )
                ),
                "date": q.created_at,
                "url": url,
                "color": status_colors.get(q.status, "#9ca3af"),
                "badge": q.get_status_display(),
            }
        )

    for p in policies:
        try:
            url = reverse("admin:policies_policy_change", args=[p.pk])
        except Exception:
            url = "#"
        status_colors = {
            "active": "#10b981",
            "past_due": "#f59e0b",
            "cancelled": "#ef4444",
            "expired": "#9ca3af",
        }
        events.append(
            {
                "type": "policy",
                "icon": "🛡️",
                "title": f"Policy {p.policy_number}",
                "description": (
                    f"{p.coverage_type.replace('-', ' ').title()} — "
                    f"${float(p.premium):,.0f} | "
                    f"{p.effective_date} → {p.expiration_date}"
                ),
                "date": p.created_at,
                "url": url,
                "color": status_colors.get(p.status, "#9ca3af"),
                "badge": p.get_status_display(),
            }
        )

    for pay in payments:
        try:
            url = reverse("admin:policies_payment_change", args=[pay.pk])
        except Exception:
            url = "#"
        status_colors = {"paid": "#10b981", "failed": "#ef4444", "pending": "#f59e0b"}
        events.append(
            {
                "type": "payment",
                "icon": "💳",
                "title": f"Payment — ${float(pay.amount):,.2f}",
                "description": f"Policy {pay.policy.policy_number} | {pay.stripe_invoice_id or ''}",
                "date": pay.paid_at,
                "url": url,
                "color": status_colors.get(pay.status, "#9ca3af"),
                "badge": pay.status.capitalize(),
            }
        )

    for claim in claims:
        try:
            url = reverse("admin:claims_claim_change", args=[claim.pk])
        except Exception:
            url = "#"
        events.append(
            {
                "type": "claim",
                "icon": "⚠️",
                "title": f"Claim #{claim.pk}",
                "description": (
                    f"Policy {claim.policy.policy_number} | "
                    + (getattr(claim, "description", "") or "")[:80]
                ),
                "date": claim.created_at,
                "url": url,
                "color": "#f97316",
                "badge": claim.get_status_display()
                if hasattr(claim, "get_status_display")
                else claim.status,
            }
        )

    for cert in certificates:
        try:
            url = reverse("admin:certificates_customcertificate_change", args=[cert.pk])
        except Exception:
            url = "#"
        events.append(
            {
                "type": "certificate",
                "icon": "📄",
                "title": "Certificate of Insurance",
                "description": (
                    f"Policy {cert.policy.policy_number} | "
                    + (getattr(cert, "holder_name", "") or "")[:60]
                ),
                "date": cert.created_at,
                "url": url,
                "color": "#6366f1",
                "badge": "COI",
            }
        )

    for dr in dunning_records:
        events.append(
            {
                "type": "dunning",
                "icon": "🔄",
                "title": f"Payment Dunning — attempt {dr.attempt_count}",
                "description": (
                    f"Policy {dr.policy.policy_number} | Status: {dr.get_status_display()}"
                ),
                "date": dr.created_at,
                "url": "#",
                "color": "#ef4444" if dr.status == "cancelled" else "#f59e0b",
                "badge": dr.get_status_display(),
            }
        )

    for notif in notifications:
        events.append(
            {
                "type": "notification",
                "icon": "🔔",
                "title": getattr(notif, "title", "Notification"),
                "description": getattr(notif, "message", "")[:80],
                "date": notif.created_at,
                "url": "#",
                "color": "#9ca3af",
                "badge": "Notification",
            }
        )

    # Sort by date descending
    events.sort(key=lambda e: e["date"], reverse=True)
    return events
