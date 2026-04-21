"""
Admin for email logs — provides searchable history of all outgoing emails.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display
from emails.models import EmailLog
from common.admin_permissions import ReadOnlyAdminMixin


@admin.register(EmailLog)
class EmailLogAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "sent_at",
        "recipient",
        "subject_truncated",
        "status_badge",
        "sent_by",
        "policy_link",
        "quote_link",
    ]
    list_display_links = ["sent_at", "recipient"]
    list_filter = ["status", "sent_at"]
    search_fields = [
        "recipient",
        "subject",
        "related_policy__policy_number",
        "related_quote__quote_number",
    ]
    ordering = ["-sent_at"]
    list_per_page = 50
    date_hierarchy = "sent_at"

    readonly_fields = [
        "recipient",
        "subject",
        "body_preview",
        "sent_at",
        "sent_by",
        "related_policy",
        "related_quote",
        "provider_message_id",
        "status",
        "error_message",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Message",
            {
                "fields": (
                    "recipient",
                    "subject",
                    "body_preview",
                    "status",
                    "error_message",
                ),
            },
        ),
        (
            "Context",
            {
                "fields": (
                    "sent_by",
                    "related_policy",
                    "related_quote",
                    "provider_message_id",
                ),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("sent_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Subject")
    def subject_truncated(self, obj):
        return obj.subject[:80] + "…" if len(obj.subject) > 80 else obj.subject

    @display(
        description="Status",
        ordering="status",
        label={
            "sent": "success",
            "failed": "danger",
            "dev_log": "warning",
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Policy")
    def policy_link(self, obj):
        if obj.related_policy_id:
            from django.urls import reverse

            url = reverse("admin:policies_policy_change", args=[obj.related_policy_id])
            return format_html(
                '<a href="{}">{}</a>', url, obj.related_policy.policy_number
            )
        return "—"

    @display(description="Quote")
    def quote_link(self, obj):
        if obj.related_quote_id:
            from django.urls import reverse

            url = reverse("admin:quotes_quote_change", args=[obj.related_quote_id])
            return format_html(
                '<a href="{}">{}</a>', url, obj.related_quote.quote_number
            )
        return "—"

    @display(description="Body Preview")
    def body_preview(self, obj):
        """Render the email body in a sandboxed iframe for preview."""
        if not obj.body:
            return "(empty)"
        # Truncate very large bodies to avoid overwhelming the page
        body = obj.body[:50000]
        return format_html(
            '<iframe srcdoc="{}" style="width:100%;min-height:400px;border:1px solid #e2e8f0;border-radius:4px;" sandbox=""></iframe>',
            body.replace('"', "&quot;"),
        )
