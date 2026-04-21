from django.contrib import admin
from django.contrib import messages
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.decorators import display

from common.admin_permissions import ReadOnlyAdminMixin, is_corgi_admin
from producers.models import Producer, PolicyProducer, CommissionPayout


@admin.register(Producer)
class ProducerAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = ["name", "producer_type", "email", "is_active_badge", "created_at"]
    list_filter = ["producer_type", "is_active"]
    search_fields = ["name", "email"]
    ordering = ["name"]
    list_per_page = 25
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Producer",
            {
                "fields": ("name", "producer_type", "email", "is_active"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Active", label=True)
    def is_active_badge(self, obj):
        if obj.is_active:
            return "active", "Active"
        return "inactive", "Inactive"

    def has_module_perms(self, request, app_label=None):
        if not is_corgi_admin(request.user):
            return False
        return (
            super().has_module_perms(request, app_label)
            if hasattr(super(), "has_module_perms")
            else True
        )

    def has_view_permission(self, request, obj=None):
        if not is_corgi_admin(request.user):
            return False
        return super().has_view_permission(request, obj)


class PolicyProducerInline(UnfoldTabularInline):
    model = PolicyProducer
    extra = 0
    show_change_link = True
    autocomplete_fields = ["producer"]
    fields = ["producer", "commission_type", "commission_rate", "commission_amount"]


@admin.register(CommissionPayout)
class CommissionPayoutAdmin(UnfoldModelAdmin):
    list_display = [
        "producer",
        "policy",
        "amount",
        "calculation_method",
        "status_badge",
        "paid_at",
        "created_at",
    ]
    list_filter = ["status", "calculation_method", "created_at"]
    search_fields = ["producer__name", "policy__policy_number", "stripe_transfer_id"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "paid_at"]
    actions = ["action_approve_payouts", "action_mark_paid"]

    fieldsets = (
        (
            "Payout",
            {
                "fields": (
                    "producer",
                    "policy",
                    "amount",
                    "calculation_method",
                    "status",
                ),
            },
        ),
        (
            "Payment Details",
            {
                "fields": ("paid_at", "stripe_transfer_id", "notes"),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Status", label=True)
    def status_badge(self, obj):
        colors = {"calculated": "warning", "approved": "info", "paid": "success"}
        return colors.get(obj.status, "secondary"), obj.get_status_display()

    @admin.action(description="Approve selected payouts")
    def action_approve_payouts(self, request, queryset):
        from producers.services import approve_payout

        count = 0
        for payout in queryset.filter(status="calculated"):
            try:
                approve_payout(payout)
                count += 1
            except ValueError as e:
                self.message_user(request, str(e), level=messages.WARNING)
        self.message_user(request, f"{count} payout(s) approved.")

    @admin.action(description="Mark selected payouts as paid")
    def action_mark_paid(self, request, queryset):
        from producers.services import mark_payout_paid

        count = 0
        for payout in queryset.filter(status="approved"):
            try:
                mark_payout_paid(payout)
                count += 1
            except ValueError as e:
                self.message_user(request, str(e), level=messages.WARNING)
        self.message_user(request, f"{count} payout(s) marked as paid.")

    def has_module_perms(self, request, app_label=None):
        if not is_corgi_admin(request.user):
            return False
        return (
            super().has_module_perms(request, app_label)
            if hasattr(super(), "has_module_perms")
            else True
        )

    def has_view_permission(self, request, obj=None):
        if not is_corgi_admin(request.user):
            return False
        return super().has_view_permission(request, obj)
