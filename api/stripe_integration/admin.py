"""
Django admin for Stripe-related models.

Provides admin actions to approve and deny refund requests,
monitors the dunning sequence for failed payments,
and a payment reconciliation dashboard view.
"""

from django.contrib import admin, messages
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html

from stripe_integration.models import DunningRecord, RefundRequest


@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "policy_link",
        "amount_display",
        "reason",
        "status_badge",
        "requested_by",
        "approved_by",
        "created_at",
    ]
    list_filter = ["status", "reason", "created_at"]
    search_fields = [
        "policy__policy_number",
        "requested_by__email",
        "approved_by__email",
        "stripe_refund_id",
    ]
    readonly_fields = [
        "stripe_refund_id",
        "stripe_payment_intent_id",
        "processed_at",
        "approved_at",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["policy", "requested_by", "approved_by"]
    actions = ["approve_refunds", "deny_refunds"]

    fieldsets = [
        (
            "Request Details",
            {
                "fields": [
                    "policy",
                    "amount",
                    "reason",
                    "reason_detail",
                    "status",
                    "requested_by",
                ]
            },
        ),
        (
            "Decision",
            {
                "fields": [
                    "approved_by",
                    "approved_at",
                    "denial_reason",
                ]
            },
        ),
        (
            "Stripe",
            {
                "fields": [
                    "stripe_payment_intent_id",
                    "stripe_refund_id",
                    "processed_at",
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def policy_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    policy_link.short_description = "Policy"

    def amount_display(self, obj):
        return f"${obj.amount:,.2f}"

    amount_display.short_description = "Amount"

    STATUS_COLORS = {
        "pending": "#f59e0b",
        "approved": "#3b82f6",
        "denied": "#ef4444",
        "processed": "#10b981",
        "failed": "#dc2626",
    }

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    @admin.action(
        description="✅ Approve selected refund requests (processes via Stripe)"
    )
    def approve_refunds(self, request, queryset):
        from stripe_integration.refund_service import RefundService

        pending = queryset.filter(status="pending")
        if not pending.exists():
            self.message_user(
                request, "No pending refund requests selected.", messages.WARNING
            )
            return

        success_count = 0
        fail_count = 0

        for rr in pending:
            try:
                RefundService.approve_refund(rr.pk, approved_by=request.user)
                success_count += 1
            except Exception as e:
                fail_count += 1
                self.message_user(
                    request,
                    f"Refund #{rr.pk} failed: {e}",
                    messages.ERROR,
                )

        if success_count:
            self.message_user(
                request,
                f"Successfully processed {success_count} refund(s).",
                messages.SUCCESS,
            )
        if fail_count:
            self.message_user(
                request,
                f"{fail_count} refund(s) failed — check logs for details.",
                messages.ERROR,
            )

    @admin.action(description="❌ Deny selected refund requests")
    def deny_refunds(self, request, queryset):
        from stripe_integration.refund_service import RefundService

        pending = queryset.filter(status="pending")
        if not pending.exists():
            self.message_user(
                request, "No pending refund requests selected.", messages.WARNING
            )
            return

        denied = 0
        for rr in pending:
            try:
                RefundService.deny_refund(
                    rr.pk,
                    denied_by=request.user,
                    denial_reason="Denied via admin bulk action.",
                )
                denied += 1
            except Exception as e:
                self.message_user(
                    request, f"Error denying #{rr.pk}: {e}", messages.ERROR
                )

        if denied:
            self.message_user(
                request,
                f"Denied {denied} refund request(s).",
                messages.SUCCESS,
            )


@admin.register(DunningRecord)
class DunningRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "policy_link",
        "attempt_count",
        "status_badge",
        "first_failed_at",
        "next_retry_at",
        "last_attempt_at",
        "failure_reason_short",
        "created_at",
    ]
    list_filter = ["status", "attempt_count", "created_at"]
    search_fields = [
        "policy__policy_number",
        "stripe_invoice_id",
        "stripe_subscription_id",
    ]
    readonly_fields = [
        "first_failed_at",
        "last_attempt_at",
        "resolved_at",
        "created_at",
        "updated_at",
    ]
    raw_id_fields = ["policy"]
    actions = ["manually_resolve_dunning"]

    fieldsets = [
        (
            "Dunning State",
            {
                "fields": [
                    "policy",
                    "status",
                    "attempt_count",
                    "next_retry_at",
                ]
            },
        ),
        (
            "Timeline",
            {
                "fields": [
                    "first_failed_at",
                    "last_attempt_at",
                    "resolved_at",
                ]
            },
        ),
        (
            "Stripe",
            {
                "fields": [
                    "stripe_invoice_id",
                    "stripe_subscription_id",
                    "failure_reason",
                ]
            },
        ),
        (
            "Notes",
            {"fields": ["notes"]},
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    def policy_link(self, obj):
        from django.urls import reverse

        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    policy_link.short_description = "Policy"

    STATUS_COLORS = {
        "active": "#f59e0b",
        "resolved": "#10b981",
        "cancelled": "#ef4444",
    }

    def status_badge(self, obj):
        color = self.STATUS_COLORS.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"

    def failure_reason_short(self, obj):
        if obj.failure_reason:
            return obj.failure_reason[:60] + (
                "…" if len(obj.failure_reason) > 60 else ""
            )
        return "—"

    failure_reason_short.short_description = "Failure Reason"

    @admin.action(
        description="✅ Manually resolve selected dunning records (mark as resolved)"
    )
    def manually_resolve_dunning(self, request, queryset):
        from django.utils import timezone as tz

        now = tz.now()
        updated = queryset.filter(status="active").update(
            status="resolved",
            resolved_at=now,
            next_retry_at=None,
        )
        self.message_user(
            request,
            f"Resolved {updated} dunning record(s).",
            messages.SUCCESS,
        )


class PaymentReconciliationAdminSite:
    """
    A standalone Django admin view for the payment reconciliation dashboard.
    Registered as a custom admin URL under /admin/stripe/reconciliation/.
    """

    pass


def payment_reconciliation_view(request):
    """
    Admin view: Payment Reconciliation Dashboard.

    Shows:
    - Expected vs collected premium by month
    - Aging receivables (30/60/90+ day buckets)
    - Collection rate trend
    - Headline metrics
    """
    from stripe_integration.reports import reconciliation_summary

    # Only accessible by staff
    if not request.user.is_staff:
        from django.http import HttpResponseForbidden

        return HttpResponseForbidden("Staff access required.")

    try:
        data = reconciliation_summary()
    except Exception as exc:
        import traceback

        data = {"error": str(exc), "traceback": traceback.format_exc()}

    context = {
        **admin.site.each_context(request),
        "title": "Payment Reconciliation Dashboard",
        "reconciliation": data,
        "opts": {"app_label": "stripe_integration"},
    }
    return render(request, "admin/stripe_integration/reconciliation.html", context)


# Hook the reconciliation view into the admin site as a custom URL
_original_get_urls = admin.site.__class__.get_urls


def _patched_get_urls(self):
    urls = _original_get_urls(self)
    custom = [
        path(
            "stripe/reconciliation/",
            self.admin_view(payment_reconciliation_view),
            name="stripe_reconciliation",
        ),
    ]
    return custom + urls


admin.site.__class__.get_urls = _patched_get_urls
