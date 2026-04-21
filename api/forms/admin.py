"""
Django admin configuration for the Form Builder.
"""

from __future__ import annotations

import json

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html, mark_safe
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.decorators import display, action

from forms.models import FormDefinition, FormSubmission


@admin.register(FormDefinition)
class FormDefinitionAdmin(UnfoldModelAdmin):
    list_display = (
        "name",
        "slug",
        "version",
        "coverage_type",
        "is_active",
        "field_count",
        "created_at",
    )
    list_filter = ("is_active", "coverage_type")
    list_editable = ("is_active",)
    search_fields = ("name", "slug", "description", "coverage_type")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = (
        "created_at",
        "updated_at",
        "fields_table",
        "logic_display",
        "mappings_table",
    )
    ordering = ("name", "-version")
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        # Always visible
        (
            None,
            {
                "fields": (
                    "name",
                    "slug",
                    "version",
                    "coverage_type",
                    "is_active",
                    "description",
                ),
            },
        ),
        # ── Tabs ──
        (
            "Fields",
            {
                "classes": ["tab"],
                "fields": ("fields", "fields_table"),
            },
        ),
        (
            "Logic",
            {
                "classes": ["tab"],
                "fields": ("conditional_logic", "logic_display"),
            },
        ),
        (
            "Mappings",
            {
                "classes": ["tab"],
                "fields": ("rating_field_mappings", "mappings_table"),
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

    actions_detail = ["duplicate_form_action"]

    @display(description="Active", label=True)
    def is_active_badge(self, obj):
        if obj.is_active:
            return "active", "Active"
        return "inactive", "Inactive"

    @admin.display(description="Fields")
    def field_count(self, obj: FormDefinition) -> int:
        if isinstance(obj.fields, list):
            return len(obj.fields)
        return 0

    @admin.display(description="Fields Table")
    def fields_table(self, obj: FormDefinition) -> str:
        if not obj.fields:
            return mark_safe('<em style="color:#6b7280">No fields defined</em>')
        rows = []
        for f in obj.fields:
            key = f.get("key", "?")
            label = f.get("label", "")
            ftype = f.get("field_type", "")
            req = (
                '<span style="color:#16a34a;font-weight:600">★</span>'
                if f.get("required")
                else '<span style="color:#d1d5db">—</span>'
            )
            rows.append(
                f'<tr style="border-top:1px solid #f3f4f6">'
                f'<td style="padding:8px 14px;font-size:12px;font-family:monospace;color:#111827">{key}</td>'
                f'<td style="padding:8px 14px;font-size:12px;color:#374151">{label}</td>'
                f'<td style="padding:8px 14px;font-size:12px;color:#6b7280">{ftype}</td>'
                f'<td style="padding:8px 14px;font-size:12px;text-align:center">{req}</td>'
                f"</tr>"
            )
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            '<thead><tr style="background:#f9fafb">'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Key</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Label</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Type</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:center">Req</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    @admin.display(description="Conditional Logic")
    def logic_display(self, obj: FormDefinition) -> str:
        if not obj.conditional_logic:
            return mark_safe(
                '<em style="color:#6b7280">No conditional logic defined</em>'
            )
        rules = (
            obj.conditional_logic
            if isinstance(obj.conditional_logic, list)
            else [obj.conditional_logic]
        )
        rows = []
        for i, rule in enumerate(rules):
            if isinstance(rule, dict):
                target = rule.get("target", rule.get("field", "?"))
                condition = rule.get("condition", rule.get("when", ""))
                action_str = rule.get("action", rule.get("then", "show"))
                rows.append(
                    f'<tr style="border-top:1px solid #f3f4f6">'
                    f'<td style="padding:8px 14px;font-size:12px;color:#111827">{i + 1}</td>'
                    f'<td style="padding:8px 14px;font-size:12px;font-family:monospace;color:#374151">{target}</td>'
                    f'<td style="padding:8px 14px;font-size:12px;color:#6b7280">{condition}</td>'
                    f'<td style="padding:8px 14px;font-size:12px;color:#374151">{action_str}</td>'
                    f"</tr>"
                )
        if not rows:
            # Fallback: show as formatted JSON
            return mark_safe(
                f'<pre style="max-height:300px;overflow:auto;font-size:12px;background:#f9fafb;padding:12px;border-radius:8px;border:1px solid #e5e7eb">'
                f"{json.dumps(obj.conditional_logic, indent=2)}</pre>"
            )
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            '<thead><tr style="background:#f9fafb">'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">#</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Target</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Condition</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Action</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    @admin.display(description="Rating Field Mappings")
    def mappings_table(self, obj: FormDefinition) -> str:
        if not obj.rating_field_mappings:
            return mark_safe('<em style="color:#6b7280">No mappings defined</em>')
        mappings = obj.rating_field_mappings
        if not isinstance(mappings, dict):
            return mark_safe(
                f'<pre style="font-size:12px;background:#f9fafb;padding:12px;border-radius:8px;border:1px solid #e5e7eb">'
                f"{json.dumps(mappings, indent=2)}</pre>"
            )
        rows = []
        for form_field, rating_input in mappings.items():
            rows.append(
                f'<tr style="border-top:1px solid #f3f4f6">'
                f'<td style="padding:8px 14px;font-size:12px;font-family:monospace;color:#111827">{form_field}</td>'
                f'<td style="padding:8px 14px;font-size:12px;text-align:center;color:#6b7280">→</td>'
                f'<td style="padding:8px 14px;font-size:12px;font-family:monospace;color:#374151">{rating_input}</td>'
                f"</tr>"
            )
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            '<thead><tr style="background:#f9fafb">'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Form Field</th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:center"></th>'
            '<th style="padding:8px 14px;font-size:11px;font-weight:600;color:#6b7280;text-transform:uppercase;text-align:left">Rating Input</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        )

    @action(description="Duplicate form (new version)")
    def duplicate_form_action(self, request, object_id):
        from forms.service import FormService

        original = FormDefinition.objects.get(pk=object_id)
        new_form = FormService.duplicate_form(object_id)
        if new_form:
            self.message_user(
                request,
                f'Duplicated "{original.name}" → v{new_form.version} (inactive)',
            )
        else:
            self.message_user(request, "Failed to duplicate form.", level="error")


@admin.register(FormSubmission)
class FormSubmissionAdmin(UnfoldModelAdmin):
    list_display = (
        "form_definition_link",
        "quote_link",
        "submitted_at",
        "data_preview",
    )
    list_filter = ("form_definition", "submitted_at")
    search_fields = ("quote__quote_number", "form_definition__name")
    readonly_fields = (
        "form_definition",
        "quote",
        "data",
        "data_table",
        "submitted_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-submitted_at",)
    list_per_page = 25
    date_hierarchy = "submitted_at"

    fieldsets = (
        (
            None,
            {
                "fields": ("form_definition", "quote", "submitted_at"),
            },
        ),
        (
            "Submitted Data",
            {
                "classes": ["tab"],
                "fields": ("data_table",),
            },
        ),
        (
            "Raw Data",
            {
                "classes": ["tab"],
                "fields": ("data",),
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

    @admin.display(description="Form Definition")
    def form_definition_link(self, obj):
        url = reverse(
            "admin:forms_formdefinition_change", args=[obj.form_definition_id]
        )
        return format_html('<a href="{}">{}</a>', url, obj.form_definition.name)

    @admin.display(description="Quote")
    def quote_link(self, obj):
        url = reverse("admin:quotes_quote_change", args=[obj.quote_id])
        return format_html('<a href="{}">{}</a>', url, obj.quote.quote_number)

    @admin.display(description="Data Preview")
    def data_preview(self, obj):
        if not obj.data:
            return "—"
        keys = list(obj.data.keys())[:5]
        preview = ", ".join(keys)
        if len(obj.data) > 5:
            preview += f" (+{len(obj.data) - 5} more)"
        return preview

    @admin.display(description="Submitted Data")
    def data_table(self, obj):
        if not obj.data:
            return mark_safe('<em style="color:#6b7280">No data</em>')
        rows = []
        for key, value in obj.data.items():
            label = key.replace("_", " ").replace("-", " ").title()
            if isinstance(value, bool):
                val_display = (
                    '<span style="color:#16a34a">Yes</span>'
                    if value
                    else '<span style="color:#6b7280">No</span>'
                )
            elif isinstance(value, list):
                val_display = (
                    ", ".join(str(v) for v in value)
                    if value
                    else '<span style="color:#6b7280">—</span>'
                )
            elif isinstance(value, dict):
                val_display = f'<pre style="margin:0;font-size:11px">{json.dumps(value, indent=2)}</pre>'
            else:
                val_display = (
                    str(value)
                    if value is not None
                    else '<span style="color:#6b7280">—</span>'
                )
            rows.append(
                f'<tr style="border-top:1px solid #f3f4f6">'
                f'<td style="padding:8px 14px;font-size:12px;font-weight:500;color:#6b7280;width:220px">{label}</td>'
                f'<td style="padding:8px 14px;font-size:12px;color:#374151">{val_display}</td>'
                f"</tr>"
            )
        return mark_safe(
            '<table style="width:100%;border-collapse:collapse;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;background:#fff">'
            "<tbody>" + "".join(rows) + "</tbody></table>"
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
