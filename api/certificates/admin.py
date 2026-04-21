import json

from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display
from django.utils.html import mark_safe

from certificates.models import CustomCertificate


@admin.register(CustomCertificate)
class CustomCertificateAdmin(UnfoldModelAdmin):
    list_display = [
        "custom_coi_number",
        "holder_name",
        "coi_number",
        "status_colored",
        "is_additional_insured",
        "revoked_at",
        "created_at",
    ]
    list_filter = ["status", "is_additional_insured", "holder_state", "created_at"]
    search_fields = [
        "custom_coi_number",
        "coi_number",
        "holder_name",
        "holder_city",
    ]
    readonly_fields = [
        "custom_coi_number",
        "created_at",
        "updated_at",
        "endorsements_display",
    ]
    raw_id_fields = ["user", "document"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        # Always visible
        (
            None,
            {
                "fields": (
                    "user",
                    "coi_number",
                    "custom_coi_number",
                    "document",
                    "status",
                )
            },
        ),
        # ── Tabs ──
        (
            "Certificate Holder",
            {
                "classes": ["tab"],
                "fields": (
                    "holder_name",
                    "holder_second_line",
                    "holder_street_address",
                    "holder_suite",
                    "holder_city",
                    "holder_state",
                    "holder_zip",
                    "is_additional_insured",
                ),
            },
        ),
        (
            "Endorsements",
            {
                "classes": ["tab"],
                "fields": (
                    "endorsements_display",
                    "service_location_job",
                    "service_location_address",
                    "service_you_provide_job",
                    "service_you_provide_service",
                ),
            },
        ),
        (
            "Revocation",
            {
                "classes": ["tab"],
                "fields": ("revoked_at",),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ["tab"],
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    @display(
        description="Status",
        ordering="status",
        label={
            "active": "success",
            "revoked": "danger",
            "expired": "info",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()

    @admin.display(description="Endorsements")
    def endorsements_display(self, obj):
        if not obj.endorsements:
            return mark_safe('<em style="color:#6b7280">No endorsements</em>')
        if isinstance(obj.endorsements, list):
            items = "".join(
                f'<li style="padding:4px 0;font-size:13px;color:#374151">{e}</li>'
                for e in obj.endorsements
            )
            return mark_safe(f'<ul style="margin:0;padding-left:20px">{items}</ul>')
        elif isinstance(obj.endorsements, dict):
            rows = []
            for key, value in obj.endorsements.items():
                label = key.replace("_", " ").title()
                rows.append(
                    f'<tr style="border-top:1px solid #f3f4f6">'
                    f'<td style="padding:8px 14px;font-size:12px;color:#6b7280;width:200px">{label}</td>'
                    f'<td style="padding:8px 14px;font-size:12px;color:#374151">{value}</td>'
                    f"</tr>"
                )
            return mark_safe(
                '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
                "<tbody>" + "".join(rows) + "</tbody></table>"
            )
        return mark_safe(
            f'<pre style="font-size:12px">{json.dumps(obj.endorsements, indent=2)}</pre>'
        )
