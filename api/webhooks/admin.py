"""
Admin configuration for webhook delivery system.
"""

from django.contrib import admin
from django.utils.html import format_html
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display

from webhooks.delivery import WebhookEndpoint, WebhookDelivery, WebhookDeliveryService


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(UnfoldModelAdmin):
    list_display = [
        "url",
        "org",
        "is_active",
        "events_count",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["url", "description", "org__name"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Endpoint",
            {
                "fields": ("url", "secret", "description", "is_active", "org"),
            },
        ),
        (
            "Events",
            {
                "fields": ("subscribed_events",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Subscribed Events")
    def events_count(self, obj):
        events = obj.subscribed_events or []
        return f"{len(events)} event(s)"


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(UnfoldModelAdmin):
    list_display = [
        "event_type",
        "endpoint_url",
        "status_colored",
        "attempts",
        "response_status",
        "last_attempt_at",
        "created_at",
    ]
    list_filter = ["status", "event_type", "created_at"]
    search_fields = ["endpoint__url", "event_type"]
    readonly_fields = [
        "endpoint",
        "event_type",
        "payload",
        "status",
        "attempts",
        "last_attempt_at",
        "response_status",
        "response_body",
        "error_message",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    actions = ["retry_selected"]

    @display(description="Endpoint URL")
    def endpoint_url(self, obj):
        return obj.endpoint.url

    @display(description="Status")
    def status_colored(self, obj):
        colors = {
            "pending": "orange",
            "delivered": "green",
            "failed": "red",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.action(description="Retry selected failed deliveries")
    def retry_selected(self, request, queryset):
        failed = queryset.filter(status=WebhookDelivery.STATUS_FAILED)
        count = 0
        for delivery in failed:
            delivery.status = WebhookDelivery.STATUS_PENDING
            delivery.attempts = 0
            delivery.save(update_fields=["status", "attempts"])
            WebhookDeliveryService.deliver(delivery)
            count += 1
        self.message_user(request, f"Retried {count} failed deliveries.")
