from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import (
    TabularInline as UnfoldTabularInline,
    StackedInline as UnfoldStackedInline,
)
from unfold.decorators import display
from django.contrib import messages
from auditlog.models import LogEntry
from django.db import transaction
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseRedirect, HttpResponse
from django import forms
from common.admin_permissions import ReadOnlyAdminMixin
from quotes.models import (
    Address,
    Company,
    Quote,
    QuoteDocument,
    CustomProduct,
    UnderwriterOverride,
    ReferralPartner,
    CoverageType,
    PromoCode,
)
from brokered.models import BrokeredQuoteRequest
from quotes.service import QuoteService
from policies.models import Policy
from policies.service import PolicyService
from stripe_integration.service import StripeService
from datetime import date
from decimal import Decimal
from common.widgets import PrettyJSONWidget, PrettyJSONField
from common.constants import CGL_COVERAGE, HNOA_COVERAGE, COVERAGE_DISPLAY_NAMES
from quotes.constants import (
    BROKERED_FORM_COVERAGE_TYPES,
    BROKERED_NO_FORM_COVERAGE_TYPES,
)

# ── Underwriting Workbench ────────────────────────────────────────────────────
# Register underwriting workbench custom admin URLs
from quotes.underwriting_admin import (
    underwriting_workbench_list,
    underwriting_workbench_detail,
)

_original_quotes_get_urls = admin.site.__class__.get_urls


def _patched_quotes_get_urls(self):
    urls = _original_quotes_get_urls(self)
    custom = [
        path(
            "quotes/underwriting-workbench/",
            self.admin_view(underwriting_workbench_list),
            name="underwriting_workbench_list",
        ),
        path(
            "quotes/underwriting-workbench/<int:quote_id>/",
            self.admin_view(underwriting_workbench_detail),
            name="underwriting_workbench_detail",
        ),
    ]
    return custom + urls


admin.site.__class__.get_urls = _patched_quotes_get_urls
# ─────────────────────────────────────────────────────────────────────────────
from rating.service import RatingService  # noqa: E402
from rating.rules import get_definition, DEFINITIONS  # noqa: E402
from documents_generator.constants import TECH_COVERAGE_CONFIG  # noqa: E402
from documents_generator.service import DocumentsGeneratorService  # noqa: E402
from s3.service import S3Service  # noqa: E402
from s3.schemas import UploadFileInput  # noqa: E402


@admin.register(Address)
class AddressAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = ["street_address_header", "city", "state", "zip", "created_at"]
    list_display_links = ["street_address_header"]
    search_fields = ["street_address", "city", "state", "zip"]
    list_filter = ["state", "created_at"]
    list_per_page = 25
    ordering = ["-created_at"]

    @display(description="Street Address", header=True)
    def street_address_header(self, obj):
        return [obj.street_address, ""]


@admin.register(Company)
class CompanyAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "legal_name_header",
        "type",
        "profit_type",
        "revenue_display",
        "employees_display",
        "is_tech_icon",
        "created_at",
    ]
    list_display_links = ["legal_name_header"]
    search_fields = [
        "entity_legal_name",
        "business_address__city",
        "business_address__state",
        "business_description",
    ]
    list_filter = ["type", "profit_type", "is_technology_company", "created_at"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 25
    ordering = ["-created_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        # Always visible
        (
            None,
            {
                "fields": (
                    "entity_legal_name",
                    "dba_name",
                    "type",
                    "profit_type",
                    "naics_code",
                    "naics_description",
                ),
            },
        ),
        # ── Tabs ──
        (
            "Address",
            {
                "classes": ["tab"],
                "fields": ("business_address",),
            },
        ),
        (
            "Financials",
            {
                "classes": ["tab"],
                "fields": (
                    "last_12_months_revenue",
                    "projected_next_12_months_revenue",
                    "full_time_employees",
                    "part_time_employees",
                    "estimated_payroll",
                ),
            },
        ),
        (
            "Structure",
            {
                "classes": ["tab"],
                "fields": (
                    "is_technology_company",
                    "has_subsidiaries",
                    "subsidiaries_explanation",
                    "planned_acquisitions",
                    "planned_acquisitions_details",
                    "business_description",
                ),
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

    @display(description="Company", header=True)
    def legal_name_header(self, obj):
        return [obj.entity_legal_name, ""]

    @display(description="Tech Co.", boolean=True)
    def is_tech_icon(self, obj):
        return obj.is_technology_company

    @display(description="Revenue")
    def revenue_display(self, obj):
        if obj.last_12_months_revenue:
            return f"${obj.last_12_months_revenue:,.0f}"
        return "—"

    @display(description="Employees")
    def employees_display(self, obj):
        parts = []
        if obj.full_time_employees:
            parts.append(f"{obj.full_time_employees} FT")
        if obj.part_time_employees:
            parts.append(f"{obj.part_time_employees} PT")
        return ", ".join(parts) if parts else "—"


class QuoteDocumentInline(UnfoldTabularInline):
    model = QuoteDocument
    extra = 0
    readonly_fields = [
        "file_type",
        "original_filename",
        "file_size",
        "mime_type",
        "s3_url",
        "created_at",
    ]
    can_delete = False
    tab = True


class CustomProductInlineForm(forms.ModelForm):
    class Meta:
        model = CustomProduct
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"style": "width: 110px;"}),
            "product_type": forms.Select(attrs={"style": "width: 100px;"}),
            "per_occurrence_limit": forms.NumberInput(attrs={"style": "width: 70px;"}),
            "aggregate_limit": forms.NumberInput(attrs={"style": "width: 70px;"}),
            "retention": forms.NumberInput(attrs={"style": "width: 70px;"}),
            "price": forms.NumberInput(attrs={"style": "width: 80px;"}),
            "carrier": forms.TextInput(attrs={"style": "width: 90px;"}),
        }


class CustomProductInline(UnfoldTabularInline):
    model = CustomProduct
    form = CustomProductInlineForm
    extra = 0
    tab = True
    fields = [
        "name",
        "product_type",
        "per_occurrence_limit",
        "aggregate_limit",
        "retention",
        "price",
        "carrier",
        "file_display",
    ]
    readonly_fields = ["file_display"]
    can_delete = True

    def file_display(self, obj):
        if obj.s3_key:
            return format_html(
                '<a href="/admin/quotes/customproduct/{}/download/" target="_blank">{}</a>',
                obj.id,
                obj.original_filename or "Download",
            )
        return "-"

    file_display.short_description = "Doc"


class BrokeredQuoteRequestInline(UnfoldTabularInline):
    model = BrokeredQuoteRequest
    extra = 0
    can_delete = False
    tab = True
    fields = [
        "coverage_type",
        "carrier",
        "status",
        "premium_amount",
        "decline_reason",
        "run_id",
        "carrier_quote_link",
        "updated_at",
    ]
    readonly_fields = [
        "coverage_type",
        "carrier",
        "status",
        "premium_amount",
        "decline_reason",
        "run_id",
        "carrier_quote_link",
        "updated_at",
    ]

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Carrier Quote")
    def carrier_quote_link(self, obj):
        if obj.quote_url:
            return format_html(
                '<a href="{}" target="_blank" rel="noopener noreferrer">View</a>',
                obj.quote_url,
            )
        return "—"


class UnderwriterOverrideInline(UnfoldStackedInline):
    model = UnderwriterOverride
    extra = 0
    tab = True
    fields = [("coverage", "multiplier", "bypass_validation"), "comment", "created_by"]
    readonly_fields = ["created_by"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "comment":
            kwargs["widget"] = forms.Textarea(
                attrs={"rows": 2, "style": "width: 100%;"}
            )
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "coverage":
            obj = getattr(request, "_editing_quote", None)
            if obj and obj.coverages:
                all_choices = dict(
                    Quote.COVERAGE_CHOICES + Quote.COMPANY_REVIEW_CHOICES
                )
                kwargs["choices"] = [
                    (c, all_choices.get(c, c)) for c in obj.coverages
                ] + Quote.COMPANY_REVIEW_CHOICES
        return super().formfield_for_choice_field(db_field, request, **kwargs)


class AddCustomProductForm(forms.Form):
    name = forms.CharField(
        max_length=255, help_text="Display name (e.g., 'Errors & Omissions')"
    )
    product_type = forms.ChoiceField(choices=CustomProduct.PRODUCT_TYPES)
    per_occurrence_limit = forms.IntegerField(
        required=False, help_text="Per occurrence limit in dollars"
    )
    aggregate_limit = forms.IntegerField(
        required=False, help_text="Aggregate limit in dollars"
    )
    retention = forms.IntegerField(
        required=False, help_text="Retention/deductible in dollars"
    )
    price = forms.DecimalField(
        max_digits=15, decimal_places=2, help_text="Annual premium for this product"
    )
    carrier = forms.CharField(
        max_length=255, required=False, help_text="Insurance carrier name"
    )
    file = forms.FileField(required=False, help_text="Policy document (PDF)")


class ApplyPromoCodeForm(forms.Form):
    promo_code = forms.CharField(
        max_length=50, help_text="Enter the promo code to apply (e.g., TEST20)"
    )


class ApproveQuoteForm(forms.Form):
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Policy effective date for payment links",
    )


class ActivateFromInvoiceForm(forms.Form):
    stripe_payment_intent_id = forms.CharField(
        label="Stripe Payment Intent ID (pi_...)",
        help_text="From the Stripe dashboard. Used to link the payment and fetch the customer ID.",
    )
    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Coverage start date (expiration = effective + 365 days).",
    )


class SimulateRatingForm(forms.Form):
    revenue = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        required=False,
        help_text="Last 12 months revenue",
    )
    employee_count = forms.IntegerField(required=False, help_text="Full-time employees")
    state = forms.CharField(
        max_length=2, required=False, help_text="Two-letter state code (e.g., CA)"
    )
    business_description = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}),
        required=False,
        help_text="Business description",
    )
    billing_frequency = forms.ChoiceField(
        choices=Quote.BILLING_FREQUENCY_CHOICES,
        required=False,
        help_text="Billing frequency (monthly has ~11.1% surcharge)",
    )
    promo_code = forms.CharField(
        max_length=50, required=False, help_text="Promo code to apply (e.g., TEST20)"
    )
    coverages = forms.MultipleChoiceField(
        choices=Quote.COVERAGE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select coverages to rate",
    )
    coverage_data = PrettyJSONField(
        required=False,
        widget=PrettyJSONWidget(attrs={"rows": 20}),
        help_text="Coverage questionnaire data (JSON)",
    )


class QuoteAdminForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = "__all__"
        JSON_STYLE = (
            'font-family: "SF Mono", Monaco, "Cascadia Code", "Roboto Mono", Consolas, monospace; '
            "font-size: 12px; line-height: 1.6; padding: 12px; border-radius: 8px; "
            "background-color: #f9fafb; color: #374151; border: 1px solid #e5e7eb; "
            "white-space: pre; overflow-x: auto; tab-size: 2; width: 100%;"
        )
        widgets = {
            "coverage_data": PrettyJSONWidget(attrs={"rows": 10, "style": JSON_STYLE}),
            "limits_retentions": PrettyJSONWidget(
                attrs={"rows": 8, "style": JSON_STYLE}
            ),
            "claims_history": PrettyJSONWidget(attrs={"rows": 6, "style": JSON_STYLE}),
            "rating_result": PrettyJSONWidget(attrs={"rows": 10, "style": JSON_STYLE}),
        }


@admin.register(Quote)
class QuoteAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    form = QuoteAdminForm
    list_display = [
        "quote_number_header",
        "company",
        "user_email",
        "status_badge",
        "coverages_display",
        "quote_amount_display",
        "referral_partner",
        "created_at",
    ]
    list_display_links = ["quote_number_header"]
    search_fields = ["quote_number", "company__entity_legal_name", "user__email"]
    list_filter = ["status", "referral_partner", "created_at"]
    readonly_fields = [
        "quote_number",
        "created_at",
        "updated_at",
        "form_data_display",
        "quote_amount",
        "coverages_badges",
        "questionnaire_display",
        "limits_retentions_table",
        "rating_result_table",
        "claims_history_display",
        "coverage_data_display",
    ]
    inlines = [
        UnderwriterOverrideInline,
        CustomProductInline,
        BrokeredQuoteRequestInline,
        QuoteDocumentInline,
    ]
    actions = ["approve_and_send_quote", "recalculate_quotes"]
    change_form_template = "admin/quotes/quote/change_form.html"
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Overview",
            {
                "classes": ["tab"],
                "fields": (
                    "quote_number",
                    "status",
                    "quote_amount",
                    "quoted_at",
                    "company",
                    "user",
                    "organization",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
        (
            "Coverages & Limits",
            {
                "classes": ["tab"],
                "fields": ("coverages_badges", "limits_retentions_table"),
            },
        ),
        (
            "Questionnaire",
            {
                "classes": ["tab"],
                "fields": (
                    "coverage_data_display",
                    "claims_history_display",
                    "questionnaire_display",
                ),
            },
        ),
        (
            "Rating",
            {
                "classes": ["tab"],
                "fields": ("rating_result_table",),
            },
        ),
        (
            "Raw Data",
            {
                "classes": ["tab"],
                "fields": ("form_data_display",),
            },
        ),
    )

    def history_view(self, request, object_id, extra_context=None):
        # Guard: Unfold renders a history link on the add-view (object_id = '').
        # The built-in history URL pattern requires a non-empty object_id (.+),
        # so reverse() raises NoReverseMatch. Return a safe redirect instead.
        if not object_id:
            from django.http import HttpResponseRedirect

            return HttpResponseRedirect("../")
        return super().history_view(request, object_id, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:quote_id>/rerun/",
                self.admin_site.admin_view(self.rerun_quote_view),
                name="quotes_quote_rerun",
            ),
            path(
                "<int:quote_id>/download-questionnaire/",
                self.admin_site.admin_view(self.download_questionnaire_view),
                name="quotes_quote_download_questionnaire",
            ),
            path(
                "<int:quote_id>/add-custom-product/",
                self.admin_site.admin_view(self.add_custom_product_view),
                name="quotes_quote_add_custom_product",
            ),
            path(
                "<int:quote_id>/duplicate/",
                self.admin_site.admin_view(self.duplicate_quote_view),
                name="quotes_quote_duplicate",
            ),
            path(
                "<int:quote_id>/apply-promo/",
                self.admin_site.admin_view(self.apply_promo_code_view),
                name="quotes_quote_apply_promo",
            ),
            path(
                "<int:quote_id>/remove-promo/",
                self.admin_site.admin_view(self.remove_promo_code_view),
                name="quotes_quote_remove_promo",
            ),
            path(
                "approve/",
                self.admin_site.admin_view(self.approve_quotes_view),
                name="quotes_quote_approve",
            ),
            path(
                "<int:quote_id>/download-sample-cgl/",
                self.admin_site.admin_view(self.download_sample_cgl_view),
                name="quotes_quote_download_sample_cgl",
            ),
            path(
                "<int:quote_id>/download-sample-tech/",
                self.admin_site.admin_view(self.download_sample_tech_view),
                name="quotes_quote_download_sample_tech",
            ),
            path(
                "<int:quote_id>/simulate/",
                self.admin_site.admin_view(self.simulate_rating_view),
                name="quotes_quote_simulate",
            ),
            path(
                "<int:quote_id>/activate-from-invoice/",
                self.admin_site.admin_view(self.activate_from_invoice_view),
                name="quotes_quote_activate_from_invoice",
            ),
        ]
        return custom_urls + urls

    def rerun_quote_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)

        try:
            rating_result = QuoteService.process_quote_rating(
                quote, send_needs_review_email=False
            )

            if rating_result and rating_result.success:
                LogEntry.objects.log_create(
                    instance=quote,
                    action=LogEntry.Action.UPDATE,
                    changes={"message": ["", "Recalculated quote rating"]},
                    actor=request.user,
                )
                self.message_user(
                    request,
                    f"Quote {quote.quote_number} recalculated successfully. New premium: ${quote.quote_amount:,.2f}",
                    messages.SUCCESS,
                )
            else:
                reasons = (
                    ", ".join([r.reason for r in (rating_result.review_reasons or [])])
                    if rating_result
                    else "Unknown error"
                )
                self.message_user(
                    request,
                    f"Quote {quote.quote_number} needs review: {reasons}",
                    messages.WARNING,
                )
        except Exception as e:
            self.message_user(
                request,
                f"Error recalculating quote {quote.quote_number}: {str(e)}",
                messages.ERROR,
            )

        return HttpResponseRedirect(
            reverse("admin:quotes_quote_change", args=[quote_id])
        )

    def download_questionnaire_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)
        text_content = DocumentsGeneratorService.generate_questionnaire_text_for_quote(
            quote
        )
        response = HttpResponse(text_content, content_type="text/plain")
        response["Content-Disposition"] = (
            f'attachment; filename="Questionnaire-{quote.quote_number}.txt"'
        )
        return response

    def download_sample_cgl_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)
        result = DocumentsGeneratorService.generate_sample_documents_for_quote(quote)
        if not result["cgl"]:
            self.message_user(
                request, "No CGL/HNOA coverages found on this quote.", messages.ERROR
            )
            return HttpResponseRedirect(
                reverse("admin:quotes_quote_change", args=[quote_id])
            )
        response = HttpResponse(result["cgl"], content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Sample-CGL-{quote.quote_number}.pdf"'
        )
        return response

    def download_sample_tech_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)
        result = DocumentsGeneratorService.generate_sample_documents_for_quote(quote)
        if not result["tech"]:
            self.message_user(
                request, "No tech coverages found on this quote.", messages.ERROR
            )
            return HttpResponseRedirect(
                reverse("admin:quotes_quote_change", args=[quote_id])
            )
        response = HttpResponse(result["tech"], content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="Sample-Tech-{quote.quote_number}.pdf"'
        )
        return response

    def _build_coverage_options(self, quote):
        current_lr = quote.limits_retentions or {}
        coverage_options = []
        for cov_id in DEFINITIONS:
            defn = get_definition(cov_id)
            if not defn:
                continue
            lr_config = defn.limits_retentions
            cov_lr = current_lr.get(cov_id, {})
            coverage_options.append(
                {
                    "id": cov_id,
                    "display_name": COVERAGE_DISPLAY_NAMES.get(cov_id, cov_id),
                    "aggregate_limits": [
                        opt.value for opt in lr_config.aggregate_limits
                    ],
                    "per_occurrence_limits": [
                        opt.value for opt in lr_config.per_occurrence_limits
                    ],
                    "retentions": [opt.value for opt in lr_config.retentions],
                    "current_aggregate": cov_lr.get("aggregate_limit"),
                    "current_per_occurrence": cov_lr.get("per_occurrence_limit"),
                    "current_retention": cov_lr.get("retention"),
                }
            )
        return coverage_options

    def _parse_limits_retentions_from_post(self, post_data):
        limits_retentions = {}
        for key, value in post_data.items():
            if not key.startswith("lr_") or not value:
                continue
            for field_name in ("aggregate_limit", "per_occurrence_limit", "retention"):
                suffix = f"_{field_name}"
                if key.endswith(suffix):
                    cov_id = key[3 : -len(suffix)]
                    if cov_id not in limits_retentions:
                        limits_retentions[cov_id] = {}
                    try:
                        limits_retentions[cov_id][field_name] = int(value)
                    except (ValueError, TypeError):
                        pass
                    break
        return limits_retentions

    def simulate_rating_view(self, request, quote_id):
        quote = Quote.objects.select_related(
            "company", "company__business_address"
        ).get(pk=quote_id)
        results = None

        initial = {
            "revenue": quote.company.last_12_months_revenue,
            "employee_count": quote.company.full_time_employees or 0,
            "state": quote.company.business_address.state
            if quote.company.business_address
            else "",
            "business_description": quote.company.business_description or "",
            "billing_frequency": quote.billing_frequency or "annual",
            "promo_code": quote.promo_code or "",
            "coverages": quote.coverages or [],
            "coverage_data": quote.coverage_data or {},
        }

        coverage_options = self._build_coverage_options(quote)

        if request.method == "POST":
            form = SimulateRatingForm(request.POST)
            if form.is_valid():
                overrides = {}
                if form.cleaned_data.get("revenue") is not None:
                    overrides["revenue"] = form.cleaned_data["revenue"]
                if form.cleaned_data.get("employee_count") is not None:
                    overrides["employee_count"] = form.cleaned_data["employee_count"]
                if form.cleaned_data.get("state"):
                    overrides["state"] = form.cleaned_data["state"]
                if form.cleaned_data.get("business_description"):
                    overrides["business_description"] = form.cleaned_data[
                        "business_description"
                    ]
                if form.cleaned_data.get("coverages"):
                    overrides["coverages"] = form.cleaned_data["coverages"]
                if form.cleaned_data.get("coverage_data") is not None:
                    overrides["coverage_data"] = form.cleaned_data["coverage_data"]

                limits_retentions = self._parse_limits_retentions_from_post(
                    request.POST
                )
                if limits_retentions:
                    overrides["limits_retentions"] = limits_retentions

                results = QuoteService.simulate_rating(quote, overrides)

                if results and results.get("coverages"):
                    enriched = {}
                    for cov_id, data in results["coverages"].items():
                        data["display_name"] = COVERAGE_DISPLAY_NAMES.get(
                            cov_id, cov_id
                        )
                        enriched[cov_id] = data
                    results["coverages"] = enriched

                # Calculate billing summary with promo and frequency
                if results and results.get("total_premium") is not None:
                    total_premium = Decimal(str(results["total_premium"]))
                    billing_freq = (
                        form.cleaned_data.get("billing_frequency") or "annual"
                    )
                    promo_code_input = (
                        form.cleaned_data.get("promo_code") or ""
                    ).strip()

                    discount_percentage = Decimal("0")
                    promo_warning = None
                    if promo_code_input:
                        promo = StripeService.get_promotion_code(promo_code_input)
                        if promo and getattr(promo, "coupon", None):
                            if getattr(promo.coupon, "percent_off", None):
                                discount_percentage = Decimal(
                                    str(promo.coupon.percent_off)
                                )
                        else:
                            promo_warning = f"Promo code '{promo_code_input}' not found or inactive — no discount applied."

                    discounted_annual = total_premium * (1 - discount_percentage / 100)
                    billing_amounts = RatingService.calculate_billing_amounts(
                        discounted_annual, billing_freq
                    )

                    discount_amount = total_premium - discounted_annual

                    results["billing_summary"] = {
                        "annual_premium": total_premium,
                        "billing_frequency": billing_freq,
                        "promo_code": promo_code_input or None,
                        "discount_percentage": discount_percentage,
                        "discount_amount": discount_amount,
                        "discounted_annual": discounted_annual,
                        "monthly_amount": billing_amounts["monthly"],
                        "annual_amount": billing_amounts["annual"],
                        "promo_warning": promo_warning,
                    }

                # Update current selections in coverage_options from POST
                for opt in coverage_options:
                    cov_lr = limits_retentions.get(opt["id"], {})
                    if cov_lr:
                        opt["current_aggregate"] = cov_lr.get(
                            "aggregate_limit", opt["current_aggregate"]
                        )
                        opt["current_per_occurrence"] = cov_lr.get(
                            "per_occurrence_limit", opt["current_per_occurrence"]
                        )
                        opt["current_retention"] = cov_lr.get(
                            "retention", opt["current_retention"]
                        )
        else:
            form = SimulateRatingForm(initial=initial)

        context = {
            "form": form,
            "quote": quote,
            "results": results,
            "coverage_options": coverage_options,
            "opts": self.model._meta,
            "title": f"Simulate Rating - {quote.quote_number}",
        }
        return render(request, "admin/quotes/quote/simulate_rating.html", context)

    def add_custom_product_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)

        if request.method == "POST":
            form = AddCustomProductForm(request.POST, request.FILES)
            if form.is_valid():
                custom_product, _ = CustomProduct.objects.update_or_create(
                    quote=quote,
                    product_type=form.cleaned_data["product_type"],
                    defaults={
                        "name": form.cleaned_data["name"],
                        "per_occurrence_limit": form.cleaned_data.get(
                            "per_occurrence_limit"
                        ),
                        "aggregate_limit": form.cleaned_data.get("aggregate_limit"),
                        "retention": form.cleaned_data.get("retention"),
                        "price": form.cleaned_data["price"],
                        "carrier": form.cleaned_data.get("carrier"),
                    },
                )

                # Handle file upload
                if form.cleaned_data.get("file"):
                    f = form.cleaned_data["file"]
                    path_prefix = f"quotes/{quote.quote_number}/custom-products"
                    result = S3Service.upload_file(
                        UploadFileInput(
                            file=f,
                            path_prefix=path_prefix,
                            original_filename=f.name,
                            content_type=getattr(
                                f, "content_type", "application/octet-stream"
                            ),
                        )
                    )

                    if result:
                        custom_product.original_filename = f.name
                        custom_product.file_size = f.size
                        custom_product.mime_type = getattr(f, "content_type", "")
                        custom_product.s3_key = result["s3_key"]
                        custom_product.s3_url = result["s3_url"]
                        custom_product.save()

                if (
                    custom_product.product_type
                    in BROKERED_FORM_COVERAGE_TYPES + BROKERED_NO_FORM_COVERAGE_TYPES
                    and custom_product.product_type in quote.coverages
                ):
                    UnderwriterOverride.objects.update_or_create(
                        quote=quote,
                        coverage=custom_product.product_type,
                        defaults={
                            "bypass_validation": True,
                            "comment": f'Auto-created: fulfilled by custom product "{custom_product.name}"',
                            "created_by": request.user,
                        },
                    )
                    if quote.status not in ("purchased", "declined"):
                        QuoteService.process_quote_rating(
                            quote, send_needs_review_email=False
                        )

                LogEntry.objects.log_create(
                    instance=quote,
                    action=LogEntry.Action.UPDATE,
                    changes={
                        "message": [
                            "",
                            f"Added custom product: {form.cleaned_data['product_type']}. Price: ${form.cleaned_data['price']}",
                        ]
                    },
                    actor=request.user,
                )
                self.message_user(
                    request,
                    f"Added custom product: {custom_product.name}",
                    messages.SUCCESS,
                )
                return redirect("admin:quotes_quote_change", quote_id)
        else:
            form = AddCustomProductForm()

        brokered_coverages = [
            COVERAGE_DISPLAY_NAMES.get(c, c)
            for c in quote.coverages
            if c in BROKERED_FORM_COVERAGE_TYPES + BROKERED_NO_FORM_COVERAGE_TYPES
        ]

        context = {
            "form": form,
            "quote": quote,
            "brokered_coverages": brokered_coverages,
            "opts": self.model._meta,
            "title": f"Add Custom Product - {quote.quote_number}",
        }
        return render(request, "admin/quotes/quote/add_custom_product.html", context)

    def duplicate_quote_view(self, request, quote_id):
        original = Quote.objects.get(pk=quote_id)

        new_quote = Quote.objects.create(
            company=original.company,
            user=original.user,
            organization=original.organization,
            status="draft",
            coverages=original.coverages,
            coverage_data=original.coverage_data,
            limits_retentions=original.limits_retentions,
            claims_history=original.claims_history,
            billing_frequency=original.billing_frequency,
            promo_code=original.promo_code,
            form_data_snapshot=original.form_data_snapshot,
            completed_steps=original.completed_steps,
            current_step=original.current_step,
        )

        LogEntry.objects.log_create(
            instance=new_quote,
            action=LogEntry.Action.CREATE,
            changes={"message": ["", f"Duplicated from quote {original.id}"]},
            actor=request.user,
        )
        self.message_user(
            request,
            f"Quote {original.quote_number} duplicated as {new_quote.quote_number}",
            messages.SUCCESS,
        )

        return HttpResponseRedirect(
            reverse("admin:quotes_quote_change", args=[new_quote.id])
        )

    def apply_promo_code_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)

        if request.method == "POST":
            form = ApplyPromoCodeForm(request.POST)
            if form.is_valid():
                promo_code = form.cleaned_data["promo_code"].strip()

                promo = StripeService.get_promotion_code(promo_code)
                if not promo:
                    self.message_user(
                        request,
                        f"Promo code '{promo_code}' not found or is inactive",
                        messages.ERROR,
                    )
                    return redirect("admin:quotes_quote_change", quote_id)

                discount_info = ""
                if promo.coupon:
                    if (
                        hasattr(promo.coupon, "percent_off")
                        and promo.coupon.percent_off
                    ):
                        discount_info = f" ({promo.coupon.percent_off}% off)"
                    elif (
                        hasattr(promo.coupon, "amount_off") and promo.coupon.amount_off
                    ):
                        discount_info = f" (${promo.coupon.amount_off / 100:.2f} off)"

                quote.promo_code = promo_code
                quote.save(update_fields=["promo_code"])

                if quote.form_data_snapshot:
                    quote.form_data_snapshot["promo_code"] = promo_code
                    quote.save(update_fields=["form_data_snapshot"])

                LogEntry.objects.log_create(
                    instance=quote,
                    action=LogEntry.Action.UPDATE,
                    changes={
                        "message": [
                            "",
                            f"Applied promo code: {form.cleaned_data['promo_code']}",
                        ]
                    },
                    actor=request.user,
                )
                self.message_user(
                    request,
                    f"Promo code '{promo_code}'{discount_info} applied to quote {quote.quote_number}",
                    messages.SUCCESS,
                )
                return redirect("admin:quotes_quote_change", quote_id)
        else:
            form = ApplyPromoCodeForm()

        context = {
            "form": form,
            "quote": quote,
            "opts": self.model._meta,
            "title": f"Apply Promo Code - {quote.quote_number}",
        }
        return render(request, "admin/quotes/quote/apply_promo_code.html", context)

    def remove_promo_code_view(self, request, quote_id):
        quote = Quote.objects.get(pk=quote_id)

        old_promo = quote.promo_code
        if not old_promo:
            self.message_user(request, "No promo code to remove", messages.WARNING)
            return redirect("admin:quotes_quote_change", quote_id)

        quote.promo_code = None
        quote.save(update_fields=["promo_code"])

        if quote.form_data_snapshot:
            quote.form_data_snapshot["promo_code"] = None
            quote.save(update_fields=["form_data_snapshot"])

        LogEntry.objects.log_create(
            instance=quote,
            action=LogEntry.Action.UPDATE,
            changes={"message": ["", "Removed promo code"]},
            actor=request.user,
        )
        self.message_user(
            request,
            f"Promo code '{old_promo}' removed from quote {quote.quote_number}",
            messages.SUCCESS,
        )
        return redirect("admin:quotes_quote_change", quote_id)

    def activate_from_invoice_view(self, request, quote_id):
        quote = get_object_or_404(Quote, pk=quote_id)

        if request.method == "POST":
            form = ActivateFromInvoiceForm(request.POST)
            if form.is_valid():
                pi_id = form.cleaned_data["stripe_payment_intent_id"]
                effective_date = form.cleaned_data["effective_date"]
                try:
                    client = StripeService.get_client()
                    pi = client.PaymentIntent.retrieve(pi_id)
                    customer_id = pi.customer
                    with transaction.atomic():
                        policies = PolicyService.create_from_direct_invoice(
                            quote, pi_id, customer_id, effective_date
                        )
                    LogEntry.objects.log_create(
                        instance=quote,
                        action=LogEntry.Action.UPDATE,
                        changes={"message": ["", "Activated from Stripe invoice"]},
                        actor=request.user,
                    )
                    self.message_user(
                        request,
                        f"Created {len(policies)} policies for {quote.quote_number}.",
                        messages.SUCCESS,
                    )
                    return redirect(
                        reverse("admin:quotes_quote_change", args=[quote_id])
                    )
                except Exception as e:
                    self.message_user(request, f"Error: {e}", messages.ERROR)
        else:
            form = ActivateFromInvoiceForm()

        breakdown = (quote.rating_result or {}).get("breakdown", {})
        coverage_summary = []
        for cov in quote.coverages or []:
            premium = breakdown.get(cov, {}).get("premium", 0)
            coverage_summary.append({"coverage": cov, "premium": premium})
        for cp in quote.custom_products.all():
            coverage_summary.append({"coverage": cp.name, "premium": cp.price})

        context = self.admin_site.each_context(request)
        context.update(
            {
                "form": form,
                "quote": quote,
                "coverage_summary": coverage_summary,
                "title": f"Activate from Invoice - {quote.quote_number}",
                "opts": self.model._meta,
            }
        )
        return render(request, "admin/quotes/quote/activate_from_invoice.html", context)

    def add_view(self, request, form_url="", extra_context=None):
        """Override add_view to prevent NoReverseMatch when object_id is None."""
        extra_context = extra_context or {}
        # Skip all the change-specific context that requires a pk
        return super().add_view(request, form_url, extra_context=extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        quote = Quote.objects.get(pk=object_id)
        extra_context["show_rerun_button"] = True
        extra_context["rerun_url"] = reverse(
            "admin:quotes_quote_rerun", args=[object_id]
        )
        extra_context["download_questionnaire_url"] = reverse(
            "admin:quotes_quote_download_questionnaire", args=[object_id]
        )
        extra_context["add_custom_product_url"] = reverse(
            "admin:quotes_quote_add_custom_product", args=[object_id]
        )
        extra_context["duplicate_url"] = reverse(
            "admin:quotes_quote_duplicate", args=[object_id]
        )
        extra_context["apply_promo_url"] = reverse(
            "admin:quotes_quote_apply_promo", args=[object_id]
        )
        extra_context["remove_promo_url"] = reverse(
            "admin:quotes_quote_remove_promo", args=[object_id]
        )
        extra_context["has_promo_code"] = bool(quote.promo_code)
        extra_context["current_promo_code"] = quote.promo_code

        coverages = set(quote.coverages or [])
        extra_context["has_cgl_coverages"] = bool(
            coverages & {CGL_COVERAGE, HNOA_COVERAGE}
        )
        extra_context["has_tech_coverages"] = bool(
            coverages & set(TECH_COVERAGE_CONFIG.keys())
        )
        extra_context["download_sample_cgl_url"] = reverse(
            "admin:quotes_quote_download_sample_cgl", args=[object_id]
        )
        extra_context["download_sample_tech_url"] = reverse(
            "admin:quotes_quote_download_sample_tech", args=[object_id]
        )
        extra_context["simulate_url"] = reverse(
            "admin:quotes_quote_simulate", args=[object_id]
        )

        extra_context["show_activate_from_invoice"] = (
            quote.status in ("quoted", "needs_review") and not quote.policies.exists()
        )
        extra_context["activate_from_invoice_url"] = reverse(
            "admin:quotes_quote_activate_from_invoice", args=[object_id]
        )

        request._editing_quote = quote
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for instance in instances:
            if isinstance(instance, UnderwriterOverride) and not instance.created_by:
                instance.created_by = request.user
            instance.save()
        formset.save_m2m()

    @admin.action(description="Approve and send quote to customer")
    def approve_and_send_quote(self, request, queryset):
        selected_ids = queryset.values_list("id", flat=True)
        selected_ids_str = ",".join(str(pk) for pk in selected_ids)
        return HttpResponseRedirect(
            f"{reverse('admin:quotes_quote_approve')}?ids={selected_ids_str}"
        )

    def approve_quotes_view(self, request):
        ids_str = request.GET.get("ids", "")
        if not ids_str:
            self.message_user(request, "No quotes selected", messages.ERROR)
            return redirect("admin:quotes_quote_changelist")

        quote_ids = [int(pk) for pk in ids_str.split(",") if pk]
        quotes = Quote.objects.filter(id__in=quote_ids)

        if request.method == "POST":
            form = ApproveQuoteForm(request.POST)
            if form.is_valid():
                effective_date = form.cleaned_data["effective_date"]
                approved = 0
                errors = []

                for quote in quotes:
                    if quote.status not in ["needs_review", "submitted"]:
                        errors.append(
                            f"{quote.quote_number}: Can only approve submitted or needs_review quotes"
                        )
                        continue

                    if not quote.quote_amount:
                        errors.append(
                            f"{quote.quote_number}: Must set quote_amount before approving"
                        )
                        continue

                    try:
                        quote.status = "quoted"
                        quote.quoted_at = timezone.now()
                        if quote.rating_result:
                            quote.rating_result["success"] = True
                        quote.save()

                        QuoteService.send_quote_ready_email(quote, effective_date)
                        LogEntry.objects.log_create(
                            instance=quote,
                            action=LogEntry.Action.UPDATE,
                            changes={"message": ["", "Approved quote"]},
                            actor=request.user,
                        )
                        approved += 1
                    except Exception as e:
                        errors.append(f"{quote.quote_number}: {str(e)}")

                if approved:
                    self.message_user(
                        request,
                        f"Successfully approved {approved} quote(s)",
                        messages.SUCCESS,
                    )
                if errors:
                    self.message_user(
                        request, f"Errors: {'; '.join(errors)}", messages.ERROR
                    )

                return redirect("admin:quotes_quote_changelist")
        else:
            form = ApproveQuoteForm(initial={"effective_date": date.today()})

        context = {
            "form": form,
            "quotes": quotes,
            "opts": self.model._meta,
            "title": "Approve Quotes - Select Effective Date",
        }
        return render(request, "admin/quotes/quote/approve_quotes.html", context)

    @admin.action(description="Recalculate quote rating")
    def recalculate_quotes(self, request, queryset):
        success_count = 0
        review_count = 0
        errors = []

        for quote in queryset:
            try:
                rating_result = QuoteService.process_quote_rating(
                    quote, send_needs_review_email=False
                )

                if rating_result and rating_result.success:
                    success_count += 1
                else:
                    review_count += 1
            except Exception as e:
                errors.append(f"{quote.quote_number}: {str(e)}")

        if success_count:
            self.message_user(
                request,
                f"Successfully recalculated {success_count} quote(s)",
                messages.SUCCESS,
            )
        if review_count:
            self.message_user(
                request, f"{review_count} quote(s) need review", messages.WARNING
            )
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", messages.ERROR)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        quote = form.instance
        needs_recalculate = False

        for cp in quote.custom_products.filter(
            product_type__in=BROKERED_FORM_COVERAGE_TYPES
            + BROKERED_NO_FORM_COVERAGE_TYPES
        ):
            if cp.product_type in quote.coverages:
                UnderwriterOverride.objects.update_or_create(
                    quote=quote,
                    coverage=cp.product_type,
                    defaults={
                        "bypass_validation": True,
                        "comment": f'Auto-created: fulfilled by custom product "{cp.name}"',
                        "created_by": request.user,
                    },
                )
                needs_recalculate = True

        if needs_recalculate and quote.status not in ("purchased", "declined"):
            QuoteService.process_quote_rating(quote, send_needs_review_email=False)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["kpi"] = {
            "total": Quote.objects.count(),
            "pending": Quote.objects.filter(status="needs_review").count(),
            "quoted": Quote.objects.filter(status="quoted").count(),
            "purchased": Quote.objects.filter(status="purchased").count(),
        }
        return super().changelist_view(request, extra_context)

    @display(description="Quote #", ordering="quote_number", header=True)
    def quote_number_header(self, obj):
        return [obj.quote_number, ""]

    def user_email(self, obj):
        return obj.user.email if obj.user else None

    user_email.short_description = "User Email"

    @display(
        description="Status",
        ordering="status",
        label={
            "draft": "info",
            "submitted": "warning",
            "needs_review": "warning",
            "quoted": "info",
            "purchased": "success",
            "declined": "danger",
            "cancelled": "danger",
            "expired": "info",
            "active": "success",
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Premium")
    def quote_amount_display(self, obj):
        if obj.quote_amount:
            return f"${obj.quote_amount:,.2f}"
        return "-"

    def coverages_display(self, obj):
        return ", ".join(obj.coverages) if obj.coverages else "-"

    coverages_display.short_description = "Coverages"

    def coverages_badges(self, obj):
        if not obj.coverages:
            return "—"
        all_choices = dict(Quote.COVERAGE_CHOICES)
        badges = []
        for c in obj.coverages:
            label = COVERAGE_DISPLAY_NAMES.get(c) or all_choices.get(c, c)
            badges.append(
                f'<span style="display:inline-block;margin:2px 4px 2px 0;padding:3px 10px;'
                f"border-radius:12px;background:#ff5c00;color:#fff;font-size:12px;"
                f'font-weight:500;white-space:nowrap;">{label}</span>'
            )
        return format_html("".join(badges))

    coverages_badges.short_description = "Coverages"

    def limits_retentions_table(self, obj):
        lr = obj.limits_retentions
        if not lr:
            return mark_safe('<span style="color:#9ca3af">No limits set</span>')
        all_choices = dict(Quote.COVERAGE_CHOICES)
        rows = []
        for cov_slug, limits in lr.items():
            if not isinstance(limits, dict):
                continue
            label = COVERAGE_DISPLAY_NAMES.get(cov_slug) or all_choices.get(
                cov_slug, cov_slug
            )
            per_occ = (
                limits.get("per_occurrence")
                or limits.get("per_occurrence_limit")
                or limits.get("perOccurrenceLimit")
                or 0
            )
            agg = (
                limits.get("aggregate")
                or limits.get("aggregate_limit")
                or limits.get("aggregateLimit")
                or 0
            )
            ret = limits.get("retention") or 0
            rows.append(
                f'<div style="padding:8px 0;border-bottom:1px solid #f3f4f6">'
                f'<div style="font-weight:600;color:#111827;margin-bottom:4px">{label}</div>'
                f'<div style="display:flex;gap:24px;color:#6b7280;font-size:13px">'
                f'<span>Per Occurrence: <strong style="color:#374151">${per_occ:,.0f}</strong></span>'
                f'<span>Aggregate: <strong style="color:#374151">${agg:,.0f}</strong></span>'
                f'<span>Retention: <strong style="color:#374151">${ret:,.0f}</strong></span>'
                f"</div></div>"
            )
        return (
            mark_safe("".join(rows))
            if rows
            else mark_safe('<span style="color:#9ca3af">No coverage limits</span>')
        )

    limits_retentions_table.short_description = "Limits & Retentions"

    def rating_result_table(self, obj):
        rr = obj.rating_result
        if not rr:
            return mark_safe('<span style="color:#9ca3af">No rating result</span>')
        all_choices = dict(Quote.COVERAGE_CHOICES)
        total = rr.get("total_premium", 0)
        breakdown = rr.get("breakdown", {})
        rows = []
        for cov_slug, data in breakdown.items():
            if not isinstance(data, dict):
                continue
            label = COVERAGE_DISPLAY_NAMES.get(cov_slug) or all_choices.get(
                cov_slug, cov_slug
            )
            premium = data.get("premium", 0)
            rows.append(
                f'<div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f3f4f6"><span style="color:#374151">{label}</span><span style="font-weight:600;color:#111827">${premium:,.2f}</span></div>'
            )
        rows.append(
            f'<div style="display:flex;justify-content:space-between;padding:8px 0;margin-top:2px"><span style="font-weight:600;color:#111827">Total</span><span style="font-weight:700;color:#ff5c00;font-size:15px">${total:,.2f}</span></div>'
        )
        return mark_safe("".join(rows))

    rating_result_table.short_description = "Rating Result"

    def claims_history_display(self, obj):
        ch = obj.claims_history
        if not ch:
            return mark_safe('<span style="color:#9ca3af">No claims history</span>')
        rows = []
        for key, value in ch.items():
            label = key.replace("_", " ").title()
            if isinstance(value, bool):
                val = '<span style="color:#16a34a">Yes</span>' if value else "No"
            elif isinstance(value, list):
                val = f"{len(value)} item(s)" if value else "None"
            elif isinstance(value, dict):
                val = f"{len(value)} field(s)"
            else:
                val = str(value) if value else "--"
            rows.append(
                f'<div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid #f3f4f6"><span style="color:#6b7280">{label}</span><span style="color:#374151">{val}</span></div>'
            )
        return (
            mark_safe("".join(rows))
            if rows
            else mark_safe('<span style="color:#9ca3af">Empty</span>')
        )

    claims_history_display.short_description = "Claims History"

    def coverage_data_display(self, obj):
        cd = obj.coverage_data
        if not cd:
            return mark_safe(
                '<span style="color:#9ca3af">No coverage questionnaire data</span>'
            )
        all_choices = dict(Quote.COVERAGE_CHOICES)
        sections = []
        for cov_slug, answers in cd.items():
            if not isinstance(answers, dict):
                continue
            label = COVERAGE_DISPLAY_NAMES.get(cov_slug) or all_choices.get(
                cov_slug, cov_slug
            )
            rows = []
            for q_key, q_val in answers.items():
                q_label = q_key.replace("_", " ").replace("-", " ").title()
                if isinstance(q_val, bool):
                    val = '<span style="color:#16a34a">Yes</span>' if q_val else "No"
                elif isinstance(q_val, list):
                    val = ", ".join(str(v) for v in q_val) if q_val else "--"
                else:
                    val = str(q_val) if q_val else "--"
                rows.append(
                    f'<div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #f8f8f8"><span style="color:#6b7280;font-size:13px">{q_label}</span><span style="color:#374151;font-size:13px">{val}</span></div>'
                )
            if rows:
                sections.append(
                    f'<div style="margin-bottom:12px"><div style="font-weight:600;color:#111827;margin-bottom:6px">{label}</div>{"".join(rows)}</div>'
                )
        return (
            mark_safe("".join(sections))
            if sections
            else mark_safe('<span style="color:#9ca3af">Empty</span>')
        )

    coverage_data_display.short_description = "Coverage Questionnaire Data"

    def form_data_display(self, obj):
        import json

        return format_html(
            "<pre>{}</pre>", json.dumps(obj.form_data_snapshot, indent=2)
        )

    form_data_display.short_description = "Complete Form Data"

    def questionnaire_display(self, obj):
        if not obj.form_data_snapshot:
            return mark_safe(
                '<span style="color:#9ca3af">No questionnaire data available</span>'
            )
        text = DocumentsGeneratorService.generate_questionnaire_text_for_quote(obj)
        return mark_safe(
            '<pre style="'
            "font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;"
            "font-size: 12px; line-height: 1.6; padding: 12px;"
            "background: #f9fafb; color: #374151; border: 1px solid #e5e7eb; border-radius: 8px;"
            "white-space: pre-wrap; overflow-x: auto; width: 100%; box-sizing: border-box;"
            f'">{text}</pre>'
        )

    questionnaire_display.short_description = "Questionnaire Answers"

    def rating_result_display(self, obj):
        import json

        if not obj.rating_result:
            return format_html("<em>No rating result</em>")
        return format_html("<pre>{}</pre>", json.dumps(obj.rating_result, indent=2))

    rating_result_display.short_description = "Rating Result"

    def custom_products_total(self, obj):
        from django.db.models import Sum

        result = obj.custom_products.aggregate(total=Sum("price"))
        total = result["total"]
        if total is None:
            return "-"
        if total > 0:
            return format_html(
                '<span style="font-weight: bold;">${:,.2f}</span>', total
            )
        return format_html('<span style="color:#999;">Awaiting quote</span>')

    custom_products_total.short_description = "Brokered Products Total"


@admin.register(CustomProduct)
class CustomProductAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "name_header",
        "quote_link",
        "product_type",
        "price_display",
        "limits_display",
        "file_link",
        "created_at",
    ]
    list_display_links = ["name_header"]
    search_fields = ["name", "quote__quote_number"]
    list_filter = ["product_type", "created_at"]
    readonly_fields = [
        "original_filename",
        "file_size",
        "mime_type",
        "s3_key",
        "s3_url",
        "created_at",
        "updated_at",
    ]

    def delete_model(self, request, obj):
        from policies.models import Policy

        if Policy.objects.filter(
            quote=obj.quote, coverage_type=obj.product_type, status="active"
        ).exists():
            self.message_user(
                request,
                f"Cannot delete '{obj.name}' — there is an active policy for this coverage. Cancel the policy first.",
                messages.ERROR,
            )
            return
        super().delete_model(request, obj)

    def get_deleted_objects(self, objs, request):
        from policies.models import Policy

        deleted, model_count, perms_needed, protected = super().get_deleted_objects(
            objs, request
        )
        for obj in objs:
            if Policy.objects.filter(
                quote=obj.quote, coverage_type=obj.product_type, status="active"
            ).exists():
                protected.append(
                    f"Active policy exists for '{obj.name}' — cancel the policy first."
                )
        return deleted, model_count, perms_needed, protected

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:product_id>/download/",
                self.admin_site.admin_view(self.download_file_view),
                name="quotes_customproduct_download",
            ),
        ]
        return custom_urls + urls

    def download_file_view(self, request, product_id):
        product = CustomProduct.objects.get(id=product_id)
        if not product.s3_key:
            messages.error(request, "No file attached to this product")
            return redirect("admin:quotes_customproduct_change", product_id)
        download_url = S3Service.generate_presigned_url(product.s3_key, expiration=60)
        if download_url:
            return redirect(download_url)
        messages.error(request, "Failed to generate download URL")
        return redirect("admin:quotes_customproduct_change", product_id)

    @display(description="Product", header=True)
    def name_header(self, obj):
        return [obj.name, ""]

    @display(description="Price")
    def price_display(self, obj):
        if obj.price:
            return f"${obj.price:,.2f}"
        return "-"

    def quote_link(self, obj):
        url = reverse("admin:quotes_quote_change", args=[obj.quote.id])
        return format_html('<a href="{}">{}</a>', url, obj.quote.quote_number)

    quote_link.short_description = "Quote"

    @display(description="Limits")
    def limits_display(self, obj):
        parts = []
        if obj.per_occurrence_limit:
            parts.append(f"Per Occ: ${obj.per_occurrence_limit:,}")
        if obj.aggregate_limit:
            parts.append(f"Agg: ${obj.aggregate_limit:,}")
        if obj.retention:
            parts.append(f"Ret: ${obj.retention:,}")
        return " | ".join(parts) if parts else "-"

    def file_link(self, obj):
        if obj.s3_key:
            url = f"/admin/quotes/customproduct/{obj.id}/download/"
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                url,
                obj.original_filename or "Download",
            )
        return "-"

    file_link.short_description = "Document"


@admin.register(QuoteDocument)
class QuoteDocumentAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "filename_header",
        "quote",
        "file_type",
        "file_size_kb",
        "created_at",
    ]
    list_display_links = ["filename_header"]
    search_fields = ["original_filename", "quote__quote_number"]
    list_filter = ["file_type", "created_at"]
    readonly_fields = [
        "quote",
        "file_type",
        "original_filename",
        "file_size",
        "mime_type",
        "s3_key",
        "s3_url",
        "created_at",
        "updated_at",
    ]

    @display(description="Filename", header=True)
    def filename_header(self, obj):
        return [obj.original_filename or "-", ""]

    def file_size_kb(self, obj):
        return f"{obj.file_size / 1024:.2f} KB"

    file_size_kb.short_description = "File Size"


@admin.register(UnderwriterOverride)
class UnderwriterOverrideAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "quote_link_header",
        "coverage_display",
        "multiplier_display",
        "bypass_icon",
        "created_by",
        "created_at",
    ]
    list_display_links = ["quote_link_header"]
    search_fields = ["quote__quote_number", "comment"]
    list_filter = ["coverage", "bypass_validation", "created_at"]
    readonly_fields = ["created_by", "created_at", "updated_at"]
    autocomplete_fields = ["quote"]

    fieldsets = (
        (
            "Override Details",
            {"fields": ("quote", "coverage", "multiplier", "bypass_validation")},
        ),
        ("Justification", {"fields": ("comment",)}),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Quote", header=True)
    def quote_link_header(self, obj):
        return [obj.quote.quote_number, ""]

    @display(description="Coverage")
    def coverage_display(self, obj):
        return obj.get_coverage_display()

    @display(description="Multiplier")
    def multiplier_display(self, obj):
        if obj.multiplier:
            return f"{obj.multiplier:.2f}x"
        return "1.00x"

    @display(description="Bypass", boolean=True)
    def bypass_icon(self, obj):
        return obj.bypass_validation

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        # Re-run rating so the admin's multiplier edit propagates to the
        # quote_amount field the customer-facing impersonation view reads
        # from. Without this the quote premium stayed on the stale price.
        try:
            QuoteService.process_quote_rating(obj.quote, send_needs_review_email=False)
        except Exception as e:
            self.message_user(
                request,
                f"Override saved, but rating rerun failed: {e}",
                messages.WARNING,
            )


class ReferralPartnerForm(forms.ModelForm):
    notification_emails_text = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={"size": 80, "placeholder": "e.g. broker@alera.com, team@alera.com"}
        ),
        label="Notification Emails",
        help_text="Comma-separated email addresses to notify on account creation and quote submission",
    )

    class Meta:
        model = ReferralPartner
        fields = "__all__"
        exclude = ["notification_emails"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.notification_emails:
            self.fields["notification_emails_text"].initial = ", ".join(
                self.instance.notification_emails
            )

    def clean_notification_emails_text(self):
        raw = self.cleaned_data.get("notification_emails_text", "")
        if not raw.strip():
            return []
        emails = [e.strip() for e in raw.split(",") if e.strip()]
        for email in emails:
            if "@" not in email or "." not in email.split("@")[-1]:
                raise forms.ValidationError(f"Invalid email: {email}")
        return emails

    def save(self, commit=True):
        self.instance.notification_emails = self.cleaned_data[
            "notification_emails_text"
        ]
        return super().save(commit)


@admin.register(ReferralPartner)
class ReferralPartnerAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    form = ReferralPartnerForm
    list_display = [
        "name_header",
        "slug",
        "commission_rate_display",
        "is_active_icon",
        "policy_count",
        "created_at",
    ]
    list_display_links = ["name_header"]
    search_fields = ["name", "slug"]
    list_filter = ["is_active"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at", "purchased_policies_display"]

    @display(description="Name", header=True)
    def name_header(self, obj):
        return [obj.name, ""]

    @display(description="Commission")
    def commission_rate_display(self, obj):
        if obj.commission_rate:
            return f"{obj.commission_rate}%"
        return "-"

    @display(description="Active", boolean=True)
    def is_active_icon(self, obj):
        return obj.is_active

    def policy_count(self, obj):
        return Policy.objects.filter(quote__referral_partner=obj).count()

    policy_count.short_description = "Purchased Policies"

    def purchased_policies_display(self, obj):
        policies = (
            Policy.objects.filter(quote__referral_partner=obj)
            .select_related("quote__company")
            .order_by("-created_at")
        )

        if not policies.exists():
            return "No purchased policies yet."

        rows = "".join(
            f"<tr>"
            f'<td><a href="/admin/policies/policy/{p.id}/change/">{p.policy_number}</a></td>'
            f"<td>{p.quote.company}</td>"
            f"<td>{p.coverage_type}</td>"
            f"<td>{p.get_billing_frequency_display()}</td>"
            f"<td>{p.effective_date}</td>"
            f"<td>{p.expiration_date}</td>"
            f"</tr>"
            for p in policies
        )

        return format_html(
            '<table style="width:100%;border-collapse:collapse">'
            '<thead><tr style="text-align:left">'
            "<th>Policy Number</th><th>Company</th><th>Coverage</th>"
            "<th>Billing</th><th>Effective</th><th>Expiration</th>"
            "</tr></thead>"
            "<tbody>{}</tbody>"
            "</table>",
            mark_safe(rows),
        )

    purchased_policies_display.short_description = "Purchased Policies"


@admin.register(CoverageType)
class CoverageTypeAdmin(UnfoldModelAdmin):
    list_display = [
        "name_header",
        "slug",
        "tier",
        "carrier_default",
        "is_active",
        "display_order",
    ]
    list_display_links = ["name_header"]
    list_filter = ["tier", "is_active"]
    search_fields = ["slug", "name", "description", "carrier_default"]
    list_editable = ["is_active", "display_order"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["display_order", "name"]
    list_per_page = 25
    prepopulated_fields = {"slug": ("name",)}

    @display(description="Name", header=True)
    def name_header(self, obj):
        return [obj.name, ""]

    fieldsets = (
        (
            "Coverage Type",
            {
                "fields": (
                    "name",
                    "slug",
                    "tier",
                    "carrier_default",
                    "is_active",
                    "display_order",
                ),
            },
        ),
        (
            "Details",
            {
                "fields": ("description",),
                "classes": ("collapse",),
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


@admin.register(PromoCode)
class PromoCodeAdmin(UnfoldModelAdmin):
    list_display = [
        "code_header",
        "discount_type",
        "discount_value_display",
        "valid_from",
        "valid_until",
        "usage_display",
        "is_active_icon",
        "validity_badge",
    ]
    list_display_links = ["code_header"]
    list_filter = ["discount_type", "is_active", "created_at"]
    search_fields = ["code", "stripe_coupon_id"]
    readonly_fields = ["use_count", "created_by", "created_at", "updated_at"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Promo Code",
            {
                "fields": ("code", "discount_type", "discount_value", "is_active"),
            },
        ),
        (
            "Stripe Integration",
            {
                "fields": ("stripe_coupon_id",),
                "classes": ("collapse",),
            },
        ),
        (
            "Validity Period",
            {
                "fields": ("valid_from", "valid_until"),
            },
        ),
        (
            "Usage Limits",
            {
                "fields": ("max_uses", "use_count"),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Code", header=True)
    def code_header(self, obj):
        return [obj.code, ""]

    @display(description="Discount")
    def discount_value_display(self, obj):
        if obj.discount_type == "percentage":
            return f"{obj.discount_value}%"
        return f"${obj.discount_value:,.2f}"

    @display(description="Usage")
    def usage_display(self, obj):
        if obj.max_uses:
            return f"{obj.use_count}/{obj.max_uses}"
        return f"{obj.use_count}/∞"

    @display(description="Active", boolean=True)
    def is_active_icon(self, obj):
        return obj.is_active

    @display(
        description="Valid",
        label={
            "valid": "success",
            "invalid": "danger",
        },
    )
    def validity_badge(self, obj):
        if obj.is_valid:
            return "valid", "✓ Valid"
        return "invalid", "✗ Invalid"

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
