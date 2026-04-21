from decimal import Decimal

from django.contrib import admin
from django.db.models import Sum, F
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.decorators import display
from django.urls import reverse
from django.utils.html import format_html

from common.admin_permissions import ReadOnlyAdminMixin
from claims.models import Claim, ClaimDocument
from s3.service import S3Service


def _fmt_currency(value):
    if value is None:
        return "—"
    try:
        return f"${Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


class ClaimDocumentInline(UnfoldTabularInline):
    model = ClaimDocument
    extra = 0
    show_change_link = True
    readonly_fields = [
        "file_type",
        "original_filename",
        "file_size",
        "mime_type",
        "s3_key",
        "download_link",
        "created_at",
    ]
    fields = [
        "original_filename",
        "file_type",
        "file_size",
        "download_link",
        "created_at",
    ]

    def download_link(self, obj):
        if obj.s3_key:
            url = S3Service.generate_presigned_url(obj.s3_key)
            if url:
                return format_html('<a href="{}" target="_blank">Download</a>', url)
        return "-"

    download_link.short_description = "Download"

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "claim_number_header",
        "organization_name",
        "policy_link",
        "status_colored",
        "incident_date",
        "loss_display",
        "total_incurred_display",
        "created_at",
    ]
    list_display_links = ["claim_number_header"]
    search_fields = [
        "claim_number",
        "organization_name",
        "email",
        "user__email",
        "policy__policy_number",
    ]
    list_filter = ["status", "loss_state", "created_at"]
    readonly_fields = ["claim_number", "user", "policy", "created_at", "updated_at"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"
    inlines = [ClaimDocumentInline]
    actions = ["mark_under_review", "close_claims"]

    fieldsets = (
        (
            "Overview",
            {
                "classes": ["tab"],
                "fields": ("claim_number", "status", "policy"),
            },
        ),
        (
            "Contact",
            {
                "classes": ["tab"],
                "fields": (
                    "organization_name",
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                ),
            },
        ),
        (
            "Details",
            {
                "classes": ["tab"],
                "fields": (
                    "description",
                    "incident_date",
                    "loss_amount_estimate",
                    "claim_report_date",
                    "loss_state",
                ),
            },
        ),
        (
            "Financials",
            {
                "classes": ["tab"],
                "fields": (
                    "paid_loss",
                    "paid_lae",
                    "case_reserve_loss",
                    "case_reserve_lae",
                ),
            },
        ),
        (
            "Resolution",
            {
                "classes": ["tab"],
                "fields": ("resolution_date", "resolution_notes", "admin_notes"),
            },
        ),
        (
            "Meta",
            {
                "classes": ["tab"],
                "fields": ("user", "created_at", "updated_at"),
            },
        ),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        open_qs = Claim.objects.exclude(status__in=["closed", "denied"])
        total_reserves = Claim.objects.aggregate(
            total=Sum(F("case_reserve_loss") + F("case_reserve_lae"))
        )["total"] or Decimal("0")

        # Calculate average resolution time for resolved claims
        resolved = Claim.objects.filter(
            resolution_date__isnull=False,
            created_at__isnull=False,
        )
        if resolved.exists():
            total_days = sum(
                (c.resolution_date - c.created_at.date()).days
                for c in resolved
                if c.resolution_date and c.created_at
            )
            avg_days = total_days / resolved.count()
            avg_resolution = f"{avg_days:.0f} days"
        else:
            avg_resolution = "—"

        extra_context["kpi"] = {
            "open": open_qs.count(),
            "total_reserves": f"${total_reserves:,.0f}",
            "avg_resolution": avg_resolution,
        }
        return super().changelist_view(request, extra_context)

    @display(description="Claim #", ordering="claim_number", header=True)
    def claim_number_header(self, obj):
        return [obj.claim_number, ""]

    @display(
        description="Status",
        ordering="status",
        label={
            "submitted": "info",
            "under_review": "warning",
            "approved": "success",
            "denied": "danger",
            "closed": "info",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()

    def policy_link(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    policy_link.short_description = "Policy"

    @display(description="Loss Est.")
    def loss_display(self, obj):
        return _fmt_currency(obj.loss_amount_estimate)

    @display(description="Total Incurred")
    def total_incurred_display(self, obj):
        total = Decimal("0")
        for field in [
            obj.paid_loss,
            obj.paid_lae,
            obj.case_reserve_loss,
            obj.case_reserve_lae,
        ]:
            if field:
                total += field
        if total == 0:
            return "—"
        return _fmt_currency(total)

    @admin.action(description="Mark as Under Review")
    def mark_under_review(self, request, queryset):
        updated = queryset.filter(status="submitted").update(status="under_review")
        self.message_user(request, f"{updated} claim(s) marked as Under Review.")

    @admin.action(description="Close Claims")
    def close_claims(self, request, queryset):
        updated = queryset.exclude(status="closed").update(status="closed")
        self.message_user(request, f"{updated} claim(s) closed.")


@admin.register(ClaimDocument)
class ClaimDocumentAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "filename_header",
        "claim_link",
        "file_type",
        "file_size_kb",
        "created_at",
    ]
    list_display_links = ["filename_header"]
    search_fields = ["original_filename", "claim__claim_number"]
    list_filter = ["file_type", "created_at"]
    readonly_fields = [
        "claim",
        "file_type",
        "original_filename",
        "file_size",
        "mime_type",
        "s3_key",
        "s3_url",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 25

    @display(description="Filename", header=True)
    def filename_header(self, obj):
        return [obj.original_filename or "-", ""]

    def claim_link(self, obj):
        url = reverse("admin:claims_claim_change", args=[obj.claim_id])
        return format_html('<a href="{}">{}</a>', url, obj.claim.claim_number)

    claim_link.short_description = "Claim"

    def file_size_kb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / 1024:.1f} KB"
        return "—"

    file_size_kb.short_description = "File Size"
