import calendar
import csv
from datetime import date, datetime, timedelta
from decimal import Decimal

from django import forms
from django.conf import settings
from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from unfold.admin import TabularInline as UnfoldTabularInline
from unfold.decorators import display
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Sum, F, Value, DecimalField, Q, Case, When
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html, mark_safe

from auditlog.models import LogEntry
from emails.schemas import SendEmailInput
from emails.service import EmailService
from policies.models import (
    Cession,
    Policy,
    Payment,
    PolicyTransaction,
    StateAllocation,
    PolicyRenewal,
    PolicyExcessLayer,
    SurplusLinesFiling,
    EarnedPremiumRecord,
)
from policies.sequences import PolicySequence, COISequence
from producers.admin import PolicyProducerInline
from policies.service import PolicyService
from documents_generator.service import DocumentsGeneratorService
from documents_generator.constants import TECH_COVERAGE_CONFIG
from stripe_integration.service import StripeService
from common.constants import (
    ADMIN_FEE_RATE,
    ALL_COVERAGES,
    CGL_COVERAGE,
    COVERAGE_DISPLAY_NAMES,
    HNOA_COVERAGE,
    NTIC_LIMIT_THRESHOLD,
    MAX_SELF_SERVE_LIMIT,
)
from rating.constants import STATE_TAX_RATES
from common.admin_permissions import (
    ReadOnlyAdminMixin,
    is_corgi_admin,
    is_corgi_full_access,
)
from quotes.models import CustomProduct
from rating.rules import get_definition
from rating.service import RatingService, CalculationContext
from rating.questionnaires import validate_questionnaire


# ── Helpers ──────────────────────────────────────────────────────────────


def _fmt_currency(value):
    """Format a decimal/int as $X,XXX.XX or -."""
    if value is None:
        return "-"
    try:
        return f"${Decimal(str(value)):,.2f}"
    except Exception:
        return str(value)


def _relative_date(dt):
    """Return a human-readable relative date string."""
    if not dt:
        return "-"
    now = timezone.now()
    if hasattr(dt, "date"):
        target = dt
    else:
        target = timezone.make_aware(datetime.combine(dt, datetime.min.time()))
    delta = now - target
    days = delta.days
    if days == 0:
        return "today"
    elif days == 1:
        return "1 day ago"
    elif days < 30:
        return f"{days} days ago"
    elif days < 365:
        months = days // 30
        return f"{months} mo ago"
    else:
        years = days // 365
        return f"{years}y ago"


# ── Forms ────────────────────────────────────────────────────────────────


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return [single_file_clean(data, initial)]


class SendDocumentsForm(forms.Form):
    subject = forms.CharField(max_length=200, initial="Your Policy Documents")
    message = forms.CharField(
        widget=forms.Textarea, initial="Please find your policy documents attached."
    )
    files = MultipleFileField()


class ApplyPromoCodeForm(forms.Form):
    promo_code = forms.CharField(max_length=50, label="Promo Code")


class ModifyLimitsForm(forms.Form):
    aggregate_limit = forms.ChoiceField(label="Aggregate Limit", choices=[])
    per_occurrence_limit = forms.ChoiceField(label="Per Occurrence Limit", choices=[])
    retention = forms.ChoiceField(label="Retention", choices=[])
    new_premium = forms.DecimalField(
        label="New Annual Premium (override)",
        max_digits=15,
        decimal_places=2,
        min_value=0,
        required=False,
    )
    reason = forms.CharField(label="Reason", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, limit_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if limit_choices:
            self.fields["aggregate_limit"].choices = limit_choices.get(
                "aggregate_limits", []
            )
            self.fields["per_occurrence_limit"].choices = limit_choices.get(
                "per_occurrence_limits", []
            )
            self.fields["retention"].choices = limit_choices.get("retentions", [])


class AddCoverageForm(forms.Form):
    coverage_type = forms.ChoiceField(label="Coverage Type", choices=[])
    is_brokered = forms.BooleanField(
        label="Brokered Coverage",
        required=False,
        help_text="Check if this coverage is brokered through an external carrier",
    )
    carrier = forms.CharField(
        label="Carrier",
        max_length=255,
        required=False,
        help_text="External carrier name (required for brokered)",
    )
    aggregate_limit = forms.IntegerField(label="Aggregate Limit", min_value=0)
    per_occurrence_limit = forms.IntegerField(label="Per Occurrence Limit", min_value=0)
    retention = forms.IntegerField(label="Retention", min_value=0)
    premium = forms.DecimalField(
        label="Annual Premium", max_digits=15, decimal_places=2, min_value=0
    )
    reason = forms.CharField(label="Reason", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, coverage_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if coverage_choices:
            self.fields["coverage_type"].choices = coverage_choices


class RemoveCoverageForm(forms.Form):
    confirm = forms.BooleanField(
        label="I confirm I want to remove this coverage", required=True
    )
    reason = forms.CharField(label="Reason", widget=forms.Textarea(attrs={"rows": 3}))


class CancelPolicyForm(forms.Form):
    confirm = forms.BooleanField(
        label="I confirm I want to cancel this policy", required=True
    )
    reason = forms.CharField(label="Reason", widget=forms.Textarea(attrs={"rows": 3}))


class BackdatePolicyForm(forms.Form):
    new_effective_date = forms.DateField(
        label="New Effective Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    reason = forms.CharField(label="Reason", widget=forms.Textarea(attrs={"rows": 3}))


class ReactivatePolicyForm(forms.Form):
    reactivation_date = forms.DateField(
        label="Reactivation Date",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    confirm = forms.BooleanField(
        label="I confirm the customer has a valid payment method and I want to reactivate this policy",
        required=True,
    )

    def clean_reactivation_date(self):
        d = self.cleaned_data["reactivation_date"]
        if d > date.today():
            raise forms.ValidationError("Reactivation date cannot be in the future.")
        return d


# ── Sequence admins ──────────────────────────────────────────────────────


@admin.register(PolicySequence)
class PolicySequenceAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = ["lob_code", "state", "year", "last_sequence"]
    list_filter = ["lob_code", "state", "year"]
    search_fields = ["lob_code", "state"]
    ordering = ["-year", "state", "lob_code"]
    list_per_page = 25


@admin.register(COISequence)
class COISequenceAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = ["state", "year", "last_sequence"]
    list_filter = ["state", "year"]
    search_fields = ["state"]
    ordering = ["-year", "state"]
    list_per_page = 25


# ── Payment ──────────────────────────────────────────────────────────────


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "stripe_invoice_id_header",
        "policy_number",
        "company",
        "amount_display",
        "status_colored",
        "paid_at",
    ]
    list_display_links = ["stripe_invoice_id_header"]
    list_filter = ["status", "paid_at"]
    search_fields = ["stripe_invoice_id", "policy__policy_number"]
    readonly_fields = ["policy", "company", "created_at", "updated_at"]
    autocomplete_fields = ["policy"]
    ordering = ["-paid_at"]
    list_per_page = 25
    date_hierarchy = "paid_at"

    def policy_number(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    policy_number.short_description = "Policy"

    @display(description="Invoice", header=True)
    def stripe_invoice_id_header(self, obj):
        return [obj.stripe_invoice_id or "-", ""]

    def company(self, obj):
        if obj.policy and obj.policy.quote and obj.policy.quote.company:
            return str(obj.policy.quote.company)
        return "-"

    company.short_description = "Company"

    @display(description="Amount")
    def amount_display(self, obj):
        return _fmt_currency(obj.amount)

    @display(
        description="Status",
        label={
            "paid": "success",
            "pending": "warning",
            "failed": "danger",
            "refunded": "info",
        },
    )
    def status_colored(self, obj):
        return obj.status


# ── Inlines ──────────────────────────────────────────────────────────────


class StateAllocationInline(UnfoldTabularInline):
    model = StateAllocation
    extra = 0
    show_change_link = True
    readonly_fields = [
        "state",
        "allocation_method",
        "allocation_percent",
        "allocated_premium",
        "allocated_policy_fee",
        "allocated_membership_fee",
        "allocated_taxes",
        "created_at",
    ]
    fields = [
        "state",
        "allocation_method",
        "allocation_percent",
        "allocated_premium",
        "allocated_taxes",
    ]


class CessionInline(UnfoldTabularInline):
    model = Cession
    extra = 0
    show_change_link = True
    readonly_fields = [
        "treaty_id",
        "reinsurance_type",
        "attachment_point",
        "ceded_premium_rate",
        "ceded_premium_amount",
        "reinsurer_name",
        "created_at",
    ]
    fields = [
        "treaty_id",
        "reinsurance_type",
        "ceded_premium_rate",
        "ceded_premium_amount",
        "reinsurer_name",
    ]


# ── Cession ──────────────────────────────────────────────────────────────


@admin.register(Cession)
class CessionAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_number",
        "treaty_id",
        "reinsurance_type",
        "attachment_point",
        "ceded_premium_rate",
        "ceded_premium_amount",
        "reinsurer_name",
    ]
    list_filter = ["reinsurance_type", "reinsurer_name"]
    search_fields = ["transaction__policy__policy_number", "treaty_id"]
    readonly_fields = [
        "transaction",
        "treaty_id",
        "reinsurance_type",
        "attachment_point",
        "ceded_premium_rate",
        "ceded_premium_amount",
        "reinsurer_name",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    list_per_page = 25

    def policy_number(self, obj):
        return obj.transaction.policy.policy_number

    policy_number.short_description = "Policy"


# ── PolicyTransaction ────────────────────────────────────────────────────


@admin.register(PolicyTransaction)
class PolicyTransactionAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_link_header",
        "transaction_type",
        "effective_date",
        "accounting_date",
        "gwp_display",
        "tax_display",
        "total_premium_display",
    ]
    list_display_links = ["policy_link_header"]
    list_filter = ["transaction_type", "effective_date", "accounting_date"]
    search_fields = ["policy__policy_number"]
    readonly_fields = [
        "policy",
        "transaction_type",
        "effective_date",
        "accounting_date",
        "gross_written_premium",
        "policy_fee_delta",
        "membership_fee_delta",
        "taxes_assessments_delta",
        "total_billed_delta",
        "tax_amount",
        "tax_rate",
        "collected_amount",
        "collected_date",
        "collector_entity",
        "admin_fee_rate",
        "admin_fee_amount",
        "admin_fee_recipient_entity",
        "commission_rate",
        "commission_amount",
        "description",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["policy"]
    ordering = ["-accounting_date", "-created_at"]
    list_per_page = 25
    date_hierarchy = "accounting_date"
    inlines = [StateAllocationInline, CessionInline]

    fieldsets = (
        (
            "Transaction",
            {
                "classes": ["tab"],
                "fields": (
                    "policy",
                    "transaction_type",
                    "effective_date",
                    "accounting_date",
                    "description",
                ),
            },
        ),
        (
            "Premium",
            {
                "classes": ["tab"],
                "fields": (
                    "gross_written_premium",
                    "tax_rate",
                    "tax_amount",
                    "policy_fee_delta",
                    "membership_fee_delta",
                    "taxes_assessments_delta",
                    "total_billed_delta",
                ),
            },
        ),
        (
            "Collection",
            {
                "classes": ["tab"],
                "fields": ("collected_amount", "collected_date", "collector_entity"),
            },
        ),
        (
            "Admin Fee",
            {
                "classes": ["tab"],
                "fields": (
                    "admin_fee_rate",
                    "admin_fee_amount",
                    "admin_fee_recipient_entity",
                ),
            },
        ),
        (
            "Commission",
            {
                "classes": ["tab"],
                "fields": ("commission_rate", "commission_amount"),
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

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if not is_corgi_admin(request.user):
            return [fs for fs in fieldsets if fs[0] != "Commission"]
        return fieldsets

    @display(description="Policy", header=True)
    def policy_link_header(self, obj):
        return [obj.policy.policy_number, ""]

    @display(description="GWP")
    def gwp_display(self, obj):
        return _fmt_currency(obj.gross_written_premium)

    @display(description="Tax")
    def tax_display(self, obj):
        return _fmt_currency(obj.tax_amount)

    @display(description="Total")
    def total_premium_display(self, obj):
        return _fmt_currency(obj.gross_written_premium + obj.tax_amount)


# ── StateAllocation ──────────────────────────────────────────────────────


@admin.register(StateAllocation)
class StateAllocationAdmin(UnfoldModelAdmin):
    list_display = [
        "policy_number",
        "state",
        "allocation_method",
        "allocation_percent",
        "allocated_premium",
        "allocated_policy_fee",
        "allocated_membership_fee",
        "allocated_taxes",
    ]
    list_filter = ["state", "allocation_method"]
    search_fields = ["transaction__policy__policy_number"]
    readonly_fields = [
        "transaction",
        "state",
        "allocation_method",
        "allocation_percent",
        "allocated_premium",
        "allocated_policy_fee",
        "allocated_membership_fee",
        "allocated_taxes",
        "created_at",
        "updated_at",
    ]
    ordering = ["state"]
    list_per_page = 25

    fieldsets = (
        (
            "Allocation",
            {
                "fields": (
                    "transaction",
                    "state",
                    "allocation_method",
                    "allocation_percent",
                ),
            },
        ),
        (
            "Amounts",
            {
                "fields": (
                    "allocated_premium",
                    "allocated_policy_fee",
                    "allocated_membership_fee",
                    "allocated_taxes",
                ),
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

    def policy_number(self, obj):
        return obj.transaction.policy.policy_number

    policy_number.short_description = "Policy"


# ── Filters ──────────────────────────────────────────────────────────────


class ReactivatedPolicyFilter(admin.SimpleListFilter):
    title = "reactivated"
    parameter_name = "reactivated"

    def lookups(self, request, model_admin):
        return (
            ("yes", "Reactivated"),
            ("no", "Never reactivated"),
        )

    def queryset(self, request, queryset):
        from django.db.models import Exists, OuterRef

        reinstate_subquery = PolicyTransaction.objects.filter(
            policy=OuterRef("pk"), transaction_type="reinstate"
        )
        if self.value() == "yes":
            return queryset.filter(Exists(reinstate_subquery))
        if self.value() == "no":
            return queryset.exclude(Exists(reinstate_subquery))
        return queryset


# ── Policy ───────────────────────────────────────────────────────────────


@admin.register(Policy)
class PolicyAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_number_header",
        "coverage_type",
        "user_email",
        "carrier",
        "premium_display",
        "status_colored",
        "is_brokered_icon",
        "billing_frequency_display",
        "effective_date",
        "expiration_date",
        "purchased_relative",
    ]
    list_display_links = ["policy_number_header"]
    search_fields = [
        "policy_number",
        "coi_number",
        "coverage_type",
        "carrier",
        "quote__quote_number",
        "quote__user__email",
        "stripe_payment_intent_id",
    ]
    list_filter = [
        "status",
        "coverage_type",
        "renewal_status",
        ReactivatedPolicyFilter,
        "is_brokered",
        "carrier",
        "billing_frequency",
        "effective_date",
        "purchased_at",
    ]
    readonly_fields = [
        "policy_number",
        "quote",
        "coverage_type",
        "coi_number",
        "premium",
        "status",
        "billing_frequency",
        "monthly_premium",
        "promo_code",
        "discount_percentage",
        "purchased_at",
        "stripe_payment_intent_id",
        "stripe_subscription_id",
        "stripe_customer_id",
        "insured_legal_name",
        "insured_fein",
        "mailing_address_display",
        "mailing_address",
        "principal_state",
        "paid_to_date",
        "hubspot_deal_id",
        "created_at",
        "updated_at",
        "policy_summary_display",
    ]
    change_form_template = "admin/policies/policy/change_form.html"
    actions = [
        "export_to_csv",
        "batch_offer_renewal",
        "batch_cancel_policies",
        "batch_endorse_renewal_status",
    ]
    inlines = [PolicyProducerInline]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "purchased_at"

    fieldsets = (
        (
            "Overview",
            {
                "classes": ["tab"],
                "fields": (
                    "policy_summary_display",
                    "policy_number",
                    "status",
                    "coverage_type",
                    "carrier",
                    "effective_date",
                    "expiration_date",
                    "purchased_at",
                    "billing_frequency",
                    "premium",
                    "monthly_premium",
                ),
            },
        ),
        (
            "Limits",
            {
                "classes": ["tab"],
                "fields": ("per_occurrence_limit", "aggregate_limit", "retention"),
            },
        ),
        (
            "Insured",
            {
                "classes": ["tab"],
                "fields": (
                    "insured_legal_name",
                    "insured_fein",
                    "mailing_address_display",
                    "principal_state",
                    "paid_to_date",
                ),
            },
        ),
        (
            "Discount",
            {
                "classes": ["tab"],
                "fields": ("promo_code", "discount_percentage"),
            },
        ),
        (
            "Stripe",
            {
                "classes": ["tab"],
                "fields": (
                    "stripe_payment_intent_id",
                    "stripe_subscription_id",
                    "stripe_customer_id",
                ),
            },
        ),
        (
            "Claims-Made",
            {
                "classes": ["tab"],
                "fields": (
                    "retroactive_date",
                    "continuity_date",
                    "prior_pending_litigation_date",
                    "extended_reporting_period_months",
                ),
            },
        ),
        (
            "Carrier Override",
            {
                "classes": ["tab"],
                "fields": ("force_ntic",),
            },
        ),
        (
            "Renewal",
            {
                "classes": ["tab"],
                "fields": ("renewal_status", "auto_renew"),
            },
        ),
        (
            "Meta",
            {
                "classes": ["tab"],
                "fields": (
                    "quote",
                    "coi_number",
                    "is_brokered",
                    "hubspot_deal_id",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        from django.db.models import Sum
        from datetime import timedelta

        today = date.today()
        active_qs = Policy.objects.filter(status="active")
        total_premium = active_qs.aggregate(t=Sum("premium"))["t"] or Decimal("0")
        extra_context["kpi"] = {
            "active": active_qs.count(),
            "total_premium": f"${total_premium:,.0f}",
            "monthly_billed": active_qs.filter(billing_frequency="monthly").count(),
            "expiring_soon": active_qs.filter(
                expiration_date__lte=today + timedelta(days=30),
                expiration_date__gte=today,
            ).count(),
        }
        return super().changelist_view(request, extra_context)

    @display(description="Policy #", ordering="policy_number", header=True)
    def policy_number_header(self, obj):
        return [obj.policy_number, ""]

    def user_email(self, obj):
        if obj.quote and obj.quote.user:
            url = reverse("admin:users_user_change", args=[obj.quote.user_id])
            return format_html('<a href="{}">{}</a>', url, obj.quote.user.email)
        return "-"

    user_email.short_description = "User"

    @display(
        description="Status",
        ordering="status",
        label={
            "active": "success",
            "past_due": "warning",
            "cancelled": "danger",
            "expired": "info",
            "non_renewed": "info",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Brokered", boolean=True)
    def is_brokered_icon(self, obj):
        return obj.is_brokered

    @display(description="Billing", ordering="billing_frequency")
    def billing_frequency_display(self, obj):
        return obj.get_billing_frequency_display()

    @display(description="Premium")
    def premium_display(self, obj):
        return _fmt_currency(obj.premium)

    @display(description="Purchased")
    def purchased_relative(self, obj):
        return _relative_date(obj.purchased_at)

    @display(description="Mailing Address")
    def policy_summary_display(self, obj):
        status_colors = {
            "active": ("#059669", "#ecfdf5"),
            "past_due": ("#d97706", "#fffbeb"),
            "cancelled": ("#dc2626", "#fef2f2"),
            "expired": ("#6b7280", "#f3f4f6"),
            "non_renewed": ("#6b7280", "#f3f4f6"),
        }
        color, bg = status_colors.get(obj.status, ("#6b7280", "#f3f4f6"))
        premium = f"${obj.premium:,.2f}" if obj.premium else "-"
        eff = obj.effective_date.strftime("%b %d, %Y") if obj.effective_date else "-"
        exp = obj.expiration_date.strftime("%b %d, %Y") if obj.expiration_date else "-"
        return mark_safe(
            '<div style="display:flex;gap:24px;align-items:flex-start;padding:4px 0">'
            '<div style="flex:1;display:flex;flex-direction:column;gap:4px">'
            f'<div style="font-size:22px;font-weight:600;color:#111827;letter-spacing:-0.5px">{obj.policy_number}</div>'
            f'<div style="font-size:13px;color:#6b7280">{obj.get_coverage_type_display() if hasattr(obj, "get_coverage_type_display") else obj.coverage_type} · {obj.carrier}</div>'
            "</div>"
            '<div style="display:flex;gap:16px;align-items:center">'
            f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">'
            f'<span style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.3px">Premium</span>'
            f'<span style="font-size:16px;font-weight:600;color:#111827">{premium}</span>'
            f"</div>"
            f'<div style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">'
            f'<span style="font-size:11px;font-weight:600;color:#9ca3af;text-transform:uppercase;letter-spacing:0.3px">Period</span>'
            f'<span style="font-size:13px;font-weight:500;color:#374151">{eff} - {exp}</span>'
            f"</div>"
            f'<span style="display:inline-flex;align-items:center;padding:4px 12px;border-radius:99px;font-size:12px;font-weight:600;background:{bg};color:{color}">{obj.get_status_display()}</span>'
            "</div>"
            "</div>"
        )

    policy_summary_display.short_description = ""

    def mailing_address_display(self, obj):
        ma = obj.mailing_address
        if not ma or not isinstance(ma, dict):
            return "-"
        parts = [
            ma.get("street", ""),
            ma.get("suite", ""),
            f"{ma.get('city', '')}, {ma.get('state', '')} {ma.get('zip', '')}",
        ]
        return mark_safe("<br>".join(p for p in parts if p.strip()))

    @admin.action(description="Export selected policies to CSV")
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="policies.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Policy Number",
                "Coverage Type",
                "User Email",
                "Status",
                "Premium",
                "Monthly Premium",
                "Billing Frequency",
                "Is Brokered",
                "Carrier",
                "Effective Date",
                "Expiration Date",
                "Purchased At",
                "COI Number",
                "Promo Code",
                "Discount %",
                "Insured Legal Name",
                "Insured FEIN",
                "Principal State",
                "Paid-to Date",
            ]
        )

        for policy in queryset.select_related("quote__user").order_by("-created_at"):
            writer.writerow(
                [
                    policy.policy_number,
                    policy.coverage_type,
                    policy.quote.user.email,
                    policy.get_status_display(),
                    policy.premium,
                    policy.monthly_premium or "",
                    policy.get_billing_frequency_display(),
                    "Yes" if policy.is_brokered else "No",
                    policy.carrier,
                    policy.effective_date,
                    policy.expiration_date,
                    policy.purchased_at,
                    policy.coi_number or "",
                    policy.promo_code or "",
                    policy.discount_percentage or "",
                    policy.insured_legal_name or "",
                    policy.insured_fein or "",
                    policy.principal_state or "",
                    policy.paid_to_date or "",
                ]
            )

        return response

    # ── Batch Actions (V3 #22) ──────────────────────────────────────────

    @admin.action(description="Batch: Mark selected policies as Renewal Offered")
    def batch_offer_renewal(self, request, queryset):
        """Move selected active policies to renewal_status=offered and send offer emails."""
        from emails.service import EmailService
        from emails.schemas import SendEmailInput

        eligible = queryset.filter(
            status="active", renewal_status__in=["not_due", "offered"]
        )
        count = 0
        errors = []

        for policy in eligible.select_related("quote__user", "quote__company"):
            try:
                policy.renewal_status = "offered"
                policy.save(update_fields=["renewal_status"])
                # Send renewal offer email
                try:
                    company_name = (
                        policy.quote.company.entity_legal_name or "Valued Customer"
                    )
                    EmailService.send_email(
                        SendEmailInput(
                            to=policy.quote.user.email,
                            subject=f"Your Policy Renewal Offer — {policy.policy_number}",
                            html_content=(
                                f"<p>Dear {company_name},</p>"
                                f"<p>Your policy <strong>{policy.policy_number}</strong> is approaching its renewal date. "
                                f"Please log in to review your renewal offer.</p>"
                                f"<p>Expiration: {policy.expiration_date}</p>"
                            ),
                        )
                    )
                except Exception:
                    pass  # email failure should not block the batch op
                count += 1
            except Exception as e:
                errors.append(f"{policy.policy_number}: {e}")

        if count:
            self.message_user(
                request,
                f"Renewal offer sent for {count} policy(ies).",
                messages.SUCCESS,
            )
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", messages.WARNING)

    @admin.action(description="Batch: Cancel selected policies")
    def batch_cancel_policies(self, request, queryset):
        """Cancel selected active/past-due policies with a batch cancellation transaction."""

        eligible = queryset.filter(status__in=["active", "past_due"])
        count = 0
        errors = []

        for policy in eligible.select_related("quote__user", "quote__company"):
            try:
                PolicyService.cancel_policy(
                    policy,
                    reason="Batch cancellation by admin",
                    cancelled_by=request.user.get_username(),
                )
                count += 1
            except Exception as e:
                errors.append(f"{policy.policy_number}: {e}")

        if count:
            self.message_user(
                request, f"{count} policy(ies) cancelled.", messages.SUCCESS
            )
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", messages.WARNING)

    @admin.action(description="Batch: Mark selected policies as Renewal Quoted")
    def batch_endorse_renewal_status(self, request, queryset):
        """Advance selected policies to renewal_status=quoted."""
        eligible = queryset.filter(status="active", renewal_status="offered")
        count = eligible.update(renewal_status="quoted")
        self.message_user(
            request, f"{count} policy(ies) advanced to Quoted status.", messages.SUCCESS
        )

    # ── End Batch Actions ───────────────────────────────────────────────

    def get_inline_instances(self, request, obj=None):
        inlines = super().get_inline_instances(request, obj)
        if not is_corgi_admin(request.user):
            inlines = [i for i in inlines if not isinstance(i, PolicyProducerInline)]
        return inlines

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        policy = Policy.objects.select_related("quote").get(pk=object_id)
        all_policies = Policy.objects.filter(quote=policy.quote)
        all_coverage_types = [p.coverage_type for p in all_policies if p.coverage_type]
        extra_context["has_cgl_coverages"] = (
            CGL_COVERAGE in all_coverage_types or HNOA_COVERAGE in all_coverage_types
        )
        extra_context["has_tech_coverages"] = any(
            c in TECH_COVERAGE_CONFIG for c in all_coverage_types
        )
        extra_context["has_promo_code"] = bool(policy.promo_code)
        extra_context["is_brokered"] = policy.is_brokered
        extra_context["can_endorse"] = (
            policy.status == "active" and not policy.is_brokered
        )
        extra_context["can_backdate"] = policy.status == "active"
        extra_context["has_sibling_policies"] = (
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
            .exclude(pk=policy.pk)
            .exists()
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "premiums-paid/",
                self.admin_site.admin_view(self.premiums_paid_view),
                name="policies_policy_premiums_paid",
            ),
            path(
                "premiums-paid/export/",
                self.admin_site.admin_view(self.export_premiums_paid_csv),
                name="policies_policy_premiums_paid_export",
            ),
            path(
                "annual-earned-premium/",
                self.admin_site.admin_view(self.annual_earned_premium_view),
                name="policies_policy_annual_earned_premium",
            ),
            path(
                "annual-earned-premium/export/",
                self.admin_site.admin_view(self.export_annual_earned_premium_csv),
                name="policies_policy_annual_earned_premium_export",
            ),
            path(
                "premium-report/",
                self.admin_site.admin_view(self.premium_report_view),
                name="policies_policy_premium_report",
            ),
            path(
                "premium-report/export/",
                self.admin_site.admin_view(self.export_premium_report_csv),
                name="policies_policy_premium_report_export",
            ),
            path(
                "payment-status/",
                self.admin_site.admin_view(self.payment_status_view),
                name="policies_policy_payment_status",
            ),
            path(
                "payment-status/export/",
                self.admin_site.admin_view(self.export_payment_status_csv),
                name="policies_policy_payment_status_export",
            ),
            path(
                "<int:policy_id>/send-documents/",
                self.admin_site.admin_view(self.send_documents_view),
                name="policies_policy_send_documents",
            ),
            path(
                "<int:policy_id>/download-coi/",
                self.admin_site.admin_view(self.download_coi_view),
                name="policies_policy_download_coi",
            ),
            path(
                "<int:policy_id>/download-cgl-policy/",
                self.admin_site.admin_view(self.download_cgl_policy_view),
                name="policies_policy_download_cgl",
            ),
            path(
                "<int:policy_id>/download-tech-policy/",
                self.admin_site.admin_view(self.download_tech_policy_view),
                name="policies_policy_download_tech",
            ),
            path(
                "<int:policy_id>/apply-promo-code/",
                self.admin_site.admin_view(self.apply_promo_code_view),
                name="policies_policy_apply_promo",
            ),
            path(
                "<int:policy_id>/endorse-modify-limits/",
                self.admin_site.admin_view(self.endorse_modify_limits_view),
                name="policies_policy_endorse_modify_limits",
            ),
            path(
                "<int:policy_id>/endorse-add-coverage/",
                self.admin_site.admin_view(self.endorse_add_coverage_view),
                name="policies_policy_endorse_add_coverage",
            ),
            path(
                "<int:policy_id>/endorse-remove-coverage/",
                self.admin_site.admin_view(self.endorse_remove_coverage_view),
                name="policies_policy_endorse_remove_coverage",
            ),
            path(
                "<int:policy_id>/cancel-policy/",
                self.admin_site.admin_view(self.cancel_policy_view),
                name="policies_policy_cancel",
            ),
            path(
                "<int:policy_id>/endorse-backdate/",
                self.admin_site.admin_view(self.endorse_backdate_policy_view),
                name="policies_policy_backdate",
            ),
            path(
                "<int:policy_id>/reactivate-policy/",
                self.admin_site.admin_view(self.reactivate_policy_view),
                name="policies_policy_reactivate",
            ),
            path(
                "renewal-pipeline/",
                self.admin_site.admin_view(self.renewal_pipeline_view),
                name="policies_policy_renewal_pipeline",
            ),
        ]
        return custom_urls + urls

    # ── All existing views preserved below ──

    def premium_report_view(self, request):
        """View showing total premium by product for RRG vs Brokered policies."""
        status_filter = request.GET.get("status", "active")

        status_clause = "AND status = %s" if status_filter != "all" else ""
        params = [status_filter] if status_filter != "all" else []

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT coverage_type, COUNT(*) as policy_count, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = false {status_clause}
                GROUP BY coverage_type
                ORDER BY total_premium DESC
            """,
                params,
            )
            rrg_premiums = [
                {
                    "coverage_type": row[0],
                    "policy_count": row[1],
                    "total_premium": row[2],
                }
                for row in cursor.fetchall()
            ]

            cursor.execute(
                f"""
                SELECT COUNT(*) as total_policies, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = false {status_clause}
            """,
                params,
            )
            row = cursor.fetchone()
            rrg_total = {"total_policies": row[0], "total_premium": row[1]}

            cursor.execute(
                f"""
                SELECT coverage_type, carrier, COUNT(*) as policy_count, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = true {status_clause}
                GROUP BY coverage_type, carrier
                ORDER BY total_premium DESC
            """,
                params,
            )
            brokered_premiums = [
                {
                    "coverage_type": row[0],
                    "carrier": row[1],
                    "policy_count": row[2],
                    "total_premium": row[3],
                }
                for row in cursor.fetchall()
            ]

            cursor.execute(
                f"""
                SELECT COUNT(*) as total_policies, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = true {status_clause}
            """,
                params,
            )
            row = cursor.fetchone()
            brokered_total = {"total_policies": row[0], "total_premium": row[1]}

        grand_total_rrg = rrg_total["total_premium"] or 0
        grand_total_brokered = brokered_total["total_premium"] or 0
        grand_total = grand_total_rrg + grand_total_brokered

        context = {
            "title": "Premium Report",
            "opts": self.model._meta,
            "status_filter": status_filter,
            "rrg_premiums": rrg_premiums,
            "rrg_total": rrg_total,
            "brokered_premiums": brokered_premiums,
            "brokered_total": brokered_total,
            "grand_total_rrg": grand_total_rrg,
            "grand_total_brokered": grand_total_brokered,
            "grand_total": grand_total,
        }
        return render(request, "admin/policies/policy/premium_report.html", context)

    def payment_status_view(self, request):
        status_filter = request.GET.get("status", "active")
        billing_filter = request.GET.get("billing", "all")

        policies = (
            Policy.objects.select_related("quote")
            .annotate(
                total_charges=Coalesce(
                    Sum("payments__amount", filter=Q(payments__amount__gt=0)),
                    Value(0),
                    output_field=DecimalField(),
                ),
                total_refunds=Coalesce(
                    Sum(
                        Case(When(payments__amount__lt=0, then=-F("payments__amount"))),
                        output_field=DecimalField(),
                    ),
                    Value(0),
                    output_field=DecimalField(),
                ),
            )
            .annotate(
                net_collected=F("total_charges") - F("total_refunds"),
            )
        )

        if status_filter and status_filter != "all":
            policies = policies.filter(status=status_filter)

        if billing_filter and billing_filter != "all":
            policies = policies.filter(billing_frequency=billing_filter)

        policies = policies.order_by("-created_at")

        all_policies = list(policies)
        total_premium = sum(p.premium for p in all_policies)
        total_charges = sum(p.total_charges for p in all_policies)
        total_refunds = sum(p.total_refunds for p in all_policies)
        total_net = total_charges - total_refunds

        paginator = Paginator(all_policies, 25)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context = {
            "title": "Payment Status",
            "opts": self.model._meta,
            "status_filter": status_filter,
            "billing_filter": billing_filter,
            "policies": page_obj,
            "page_obj": page_obj,
            "total_premium": total_premium,
            "total_charges": total_charges,
            "total_refunds": total_refunds,
            "total_net": total_net,
        }
        return render(request, "admin/policies/policy/payment_status.html", context)

    def premiums_paid_view(self, request):
        admin_fee_rate = Decimal(ADMIN_FEE_RATE)

        try:
            year = int(request.GET.get("year", datetime.now().year))
            month = int(request.GET.get("month", datetime.now().month))
        except ValueError:
            year = datetime.now().year
            month = datetime.now().month

        include_brokered = request.GET.get("include_brokered") == "on"

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        policy_qs = Policy.objects.filter(
            effective_date__lte=last_day,
            expiration_date__gte=first_day,
        )
        payment_qs = Payment.objects.filter(
            paid_at__year=year,
            paid_at__month=month,
        ).filter(
            Q(status="paid")
            | Q(status="refunded", stripe_invoice_id__startswith="pyr_")
        )
        if not include_brokered:
            policy_qs = policy_qs.filter(is_brokered=False)
            payment_qs = payment_qs.filter(policy__is_brokered=False)

        policies = policy_qs.select_related(
            "quote__company__business_address"
        ).order_by("policy_number")

        cash_by_policy = dict(
            payment_qs.values_list("policy_id")
            .annotate(total=Sum("amount"))
            .values_list("policy_id", "total")
        )

        total_cash_collected = payment_qs.aggregate(t=Sum("amount"))["t"] or Decimal(
            "0.00"
        )

        all_policies = []
        total_earned_premium = Decimal("0.00")
        total_admin_fees = Decimal("0.00")
        total_premium_portion = Decimal("0.00")

        for policy in policies:
            period_start = max(policy.effective_date, first_day)
            period_end = min(policy.expiration_date, last_day)
            period_end_exclusive = min(
                policy.expiration_date, last_day + timedelta(days=1)
            )
            active_days = (period_end_exclusive - period_start).days
            total_days = (policy.expiration_date - policy.effective_date).days

            if total_days <= 0 or active_days <= 0:
                continue

            if policy.billing_frequency == "monthly":
                monthly_premium = policy.monthly_premium or (
                    policy.premium / 12
                ).quantize(Decimal("0.01"))
                days_in_month = calendar.monthrange(year, month)[1]
                earned_premium = (
                    monthly_premium * Decimal(active_days) / Decimal(days_in_month)
                ).quantize(Decimal("0.01"))
            else:
                monthly_premium = None
                earned_premium = (
                    policy.premium * Decimal(active_days) / Decimal(total_days)
                ).quantize(Decimal("0.01"))

            state = policy.principal_state
            if not state:
                try:
                    state = policy.quote.company.business_address.state
                except (AttributeError, TypeError):
                    state = None

            tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            earned_gwp = earned_premium / tax_multiplier
            admin_fee = (earned_gwp * admin_fee_rate).quantize(Decimal("0.01"))
            premium_portion = earned_premium - admin_fee
            cash_collected = cash_by_policy.get(policy.id, Decimal("0.00"))

            billing_premium = (
                monthly_premium
                if policy.billing_frequency == "monthly"
                else policy.premium
            )

            policy.period_start = period_start
            policy.period_end = period_end
            policy.active_days = active_days
            policy.billing_premium = billing_premium
            policy.earned_premium = earned_premium
            policy.admin_fee = admin_fee
            policy.premium_portion = premium_portion
            policy.cash_collected = cash_collected

            total_earned_premium += earned_premium
            total_admin_fees += admin_fee
            total_premium_portion += premium_portion

            all_policies.append(policy)

        paginator = Paginator(all_policies, 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context = {
            "title": "Earned Premium Revenue",
            "opts": self.model._meta,
            "selected_year": year,
            "selected_month": month,
            "include_brokered": include_brokered,
            "years": range(2023, datetime.now().year + 2),
            "months": [
                (1, "January"),
                (2, "February"),
                (3, "March"),
                (4, "April"),
                (5, "May"),
                (6, "June"),
                (7, "July"),
                (8, "August"),
                (9, "September"),
                (10, "October"),
                (11, "November"),
                (12, "December"),
            ],
            "policies": page_obj,
            "page_obj": page_obj,
            "total_earned_premium": total_earned_premium,
            "total_admin_fees": total_admin_fees,
            "total_premium_portion": total_premium_portion,
            "total_cash_collected": total_cash_collected,
        }
        return render(
            request, "admin/policies/policy/premiums_paid_report.html", context
        )

    def export_premiums_paid_csv(self, request):
        admin_fee_rate = Decimal(ADMIN_FEE_RATE)

        try:
            year = int(request.GET.get("year", datetime.now().year))
            month = int(request.GET.get("month", datetime.now().month))
        except ValueError:
            year = datetime.now().year
            month = datetime.now().month

        include_brokered = request.GET.get("include_brokered") == "on"

        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        policy_qs = Policy.objects.filter(
            effective_date__lte=last_day,
            expiration_date__gte=first_day,
        )
        payment_qs = Payment.objects.filter(
            paid_at__year=year,
            paid_at__month=month,
        ).filter(
            Q(status="paid")
            | Q(status="refunded", stripe_invoice_id__startswith="pyr_")
        )
        if not include_brokered:
            policy_qs = policy_qs.filter(is_brokered=False)
            payment_qs = payment_qs.filter(policy__is_brokered=False)

        policies = policy_qs.select_related(
            "quote__company__business_address"
        ).order_by("policy_number")

        cash_by_policy = dict(
            payment_qs.values_list("policy_id")
            .annotate(total=Sum("amount"))
            .values_list("policy_id", "total")
        )

        payment_qs.aggregate(t=Sum("amount"))["t"] or Decimal("0.00")

        rows = []
        written_policy_ids = set()
        total_earned_premium = Decimal("0.00")
        total_admin_fees = Decimal("0.00")
        total_premium_portion = Decimal("0.00")

        for policy in policies:
            period_start = max(policy.effective_date, first_day)
            period_end = min(policy.expiration_date, last_day)
            period_end_exclusive = min(
                policy.expiration_date, last_day + timedelta(days=1)
            )
            active_days = (period_end_exclusive - period_start).days
            total_days = (policy.expiration_date - policy.effective_date).days

            if total_days <= 0 or active_days <= 0:
                continue

            if policy.billing_frequency == "monthly":
                monthly_premium = policy.monthly_premium or (
                    policy.premium / 12
                ).quantize(Decimal("0.01"))
                days_in_month = calendar.monthrange(year, month)[1]
                earned_premium = (
                    monthly_premium * Decimal(active_days) / Decimal(days_in_month)
                ).quantize(Decimal("0.01"))
            else:
                monthly_premium = None
                earned_premium = (
                    policy.premium * Decimal(active_days) / Decimal(total_days)
                ).quantize(Decimal("0.01"))

            state = policy.principal_state
            if not state:
                try:
                    state = policy.quote.company.business_address.state
                except (AttributeError, TypeError):
                    state = None

            tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
            earned_gwp = earned_premium / tax_multiplier
            admin_fee = (earned_gwp * admin_fee_rate).quantize(Decimal("0.01"))
            premium_portion = earned_premium - admin_fee
            cash_collected = cash_by_policy.get(policy.id, Decimal("0.00"))
            billing_premium = (
                monthly_premium
                if policy.billing_frequency == "monthly"
                else policy.premium
            )

            total_earned_premium += earned_premium
            total_admin_fees += admin_fee
            total_premium_portion += premium_portion
            written_policy_ids.add(policy.id)

            rows.append(
                [
                    policy.policy_number,
                    policy.coverage_type,
                    policy.get_billing_frequency_display(),
                    policy.effective_date.strftime("%Y-%m-%d"),
                    policy.expiration_date.strftime("%Y-%m-%d"),
                    period_start.strftime("%Y-%m-%d"),
                    period_end.strftime("%Y-%m-%d"),
                    active_days,
                    total_days,
                    f"${billing_premium}",
                    f"${earned_premium}",
                    f"${admin_fee}",
                    f"${premium_portion}",
                    f"${cash_collected}",
                ]
            )

        unmatched_policy_ids = set(cash_by_policy.keys()) - written_policy_ids
        if unmatched_policy_ids:
            unmatched_policies = Policy.objects.filter(id__in=unmatched_policy_ids)
            for policy in unmatched_policies:
                cash_collected = cash_by_policy.get(policy.id, Decimal("0.00"))
                billing_premium = (
                    policy.monthly_premium
                    if policy.billing_frequency == "monthly"
                    else policy.premium
                )
                total_days = (policy.expiration_date - policy.effective_date).days
                rows.append(
                    [
                        policy.policy_number,
                        policy.coverage_type,
                        policy.get_billing_frequency_display(),
                        policy.effective_date.strftime("%Y-%m-%d"),
                        policy.expiration_date.strftime("%Y-%m-%d"),
                        "",
                        "",
                        0,
                        total_days,
                        f"${billing_premium}",
                        "$0.00",
                        "$0.00",
                        "$0.00",
                        f"${cash_collected}",
                    ]
                )

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="earned_premium_{year}_{month:02d}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Policy Number",
                "Coverage Type",
                "Billing Frequency",
                "Policy Start Date",
                "Policy End Date",
                "Period Start",
                "Period End",
                "Active Days",
                "Total Days",
                "Billing Premium",
                "Earned Premium",
                "Admin Fee",
                "Premium Portion",
                "Cash Collected",
            ]
        )
        writer.writerows(rows)

        return response

    def _compute_annual_earned_schedule(self, year, include_brokered):
        admin_fee_rate = Decimal(ADMIN_FEE_RATE)
        year_start = date(year, 1, 1)
        year_end = date(year, 12, 31)

        policy_qs = (
            Policy.objects.filter(
                billing_frequency="annual",
                effective_date__lte=year_end,
                expiration_date__gte=year_start,
            )
            .select_related("quote__company__business_address")
            .order_by("policy_number")
        )

        if not include_brokered:
            policy_qs = policy_qs.filter(is_brokered=False)

        month_names = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]

        rows = []
        monthly_totals = {m: Decimal("0.00") for m in range(1, 13)}
        grand_total_earned = Decimal("0.00")
        grand_total_admin_fee = Decimal("0.00")
        grand_total_premium_portion = Decimal("0.00")

        for policy in policy_qs:
            total_days = (policy.expiration_date - policy.effective_date).days
            if total_days <= 0:
                continue

            state = policy.principal_state
            if not state:
                try:
                    state = policy.quote.company.business_address.state
                except (AttributeError, TypeError):
                    state = None
            tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))

            earned_by_month = {}
            policy_year_total = Decimal("0.00")
            has_any_overlap = False

            for month in range(1, 13):
                first_day = date(year, month, 1)
                last_day = date(year, month, calendar.monthrange(year, month)[1])
                period_start = max(policy.effective_date, first_day)
                period_end_excl = min(
                    policy.expiration_date, last_day + timedelta(days=1)
                )
                active_days = max(0, (period_end_excl - period_start).days)

                if active_days > 0:
                    earned = (
                        policy.premium * Decimal(active_days) / Decimal(total_days)
                    ).quantize(Decimal("0.01"))
                    has_any_overlap = True
                else:
                    earned = None

                earned_by_month[month] = earned
                if earned:
                    policy_year_total += earned

            if not has_any_overlap:
                continue

            earned_gwp = policy_year_total / tax_multiplier
            admin_fee = (earned_gwp * admin_fee_rate).quantize(Decimal("0.01"))
            premium_portion = policy_year_total - admin_fee

            grand_total_earned += policy_year_total
            grand_total_admin_fee += admin_fee
            grand_total_premium_portion += premium_portion
            for month in range(1, 13):
                if earned_by_month[month]:
                    monthly_totals[month] += earned_by_month[month]

            rows.append(
                {
                    "policy": policy,
                    "earned_by_month": [earned_by_month[m] for m in range(1, 13)],
                    "year_total": policy_year_total,
                    "admin_fee": admin_fee,
                    "premium_portion": premium_portion,
                }
            )

        return {
            "rows": rows,
            "month_names": month_names,
            "monthly_totals": [monthly_totals[m] for m in range(1, 13)],
            "grand_total_earned": grand_total_earned,
            "grand_total_admin_fee": grand_total_admin_fee,
            "grand_total_premium_portion": grand_total_premium_portion,
        }

    def annual_earned_premium_view(self, request):
        try:
            year = int(request.GET.get("year", datetime.now().year))
        except ValueError:
            year = datetime.now().year

        include_brokered = request.GET.get("include_brokered") == "on"
        data = self._compute_annual_earned_schedule(year, include_brokered)

        paginator = Paginator(data["rows"], 50)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        context = {
            "title": "Annual Policy Earned Premium Schedule",
            "opts": self.model._meta,
            "selected_year": year,
            "include_brokered": include_brokered,
            "years": range(2023, datetime.now().year + 2),
            "month_names": data["month_names"],
            "monthly_totals": data["monthly_totals"],
            "page_obj": page_obj,
            "rows": page_obj,
            "grand_total_earned": data["grand_total_earned"],
            "grand_total_admin_fee": data["grand_total_admin_fee"],
            "grand_total_premium_portion": data["grand_total_premium_portion"],
        }
        return render(
            request, "admin/policies/policy/annual_earned_premium_report.html", context
        )

    def export_annual_earned_premium_csv(self, request):
        try:
            year = int(request.GET.get("year", datetime.now().year))
        except ValueError:
            year = datetime.now().year

        include_brokered = request.GET.get("include_brokered") == "on"
        data = self._compute_annual_earned_schedule(year, include_brokered)

        month_names = data["month_names"]
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="annual_earned_premium_{year}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Policy Number",
                "Coverage Type",
                "Policy Start",
                "Policy End",
                "Annual Premium",
                *month_names,
                "Year Total Earned",
                "Admin Fee",
                "Premium Portion",
            ]
        )

        for row in data["rows"]:
            policy = row["policy"]
            month_values = [
                f"${v}" if v is not None else "" for v in row["earned_by_month"]
            ]
            writer.writerow(
                [
                    policy.policy_number,
                    policy.coverage_type,
                    policy.effective_date.strftime("%Y-%m-%d"),
                    policy.expiration_date.strftime("%Y-%m-%d"),
                    f"${policy.premium}",
                    *month_values,
                    f"${row['year_total']}",
                    f"${row['admin_fee']}",
                    f"${row['premium_portion']}",
                ]
            )

        monthly_total_values = [f"${v}" if v else "" for v in data["monthly_totals"]]
        writer.writerow(
            [
                "TOTAL",
                "",
                "",
                "",
                "",
                *monthly_total_values,
                f"${data['grand_total_earned']}",
                f"${data['grand_total_admin_fee']}",
                f"${data['grand_total_premium_portion']}",
            ]
        )

        return response

    def _require_full_access(self, request, policy_id):
        if not is_corgi_full_access(request.user):
            self.message_user(
                request,
                "You do not have permission to perform this action.",
                messages.ERROR,
            )
            return redirect("admin:policies_policy_change", policy_id)
        return None

    def send_documents_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.get(id=policy_id)
        user = policy.quote.user

        if request.method == "POST":
            form = SendDocumentsForm(request.POST, request.FILES)
            if form.is_valid():
                attachments = []
                for f in form.cleaned_data["files"]:
                    attachments.append(
                        {
                            "filename": f.name,
                            "content": list(f.read()),
                        }
                    )

                try:
                    EmailService.send(
                        SendEmailInput(
                            to=[user.email],
                            subject=form.cleaned_data["subject"],
                            html=f"""
                            <p>Hi {user.get_full_name()},</p>
                            <p>{form.cleaned_data["message"]}</p>
                            <p>Policy Number: <strong>{policy.policy_number}</strong></p>
                            <p>Best regards,<br>Corgi Team</p>
                        """,
                            from_email=settings.HELLO_CORGI_EMAIL,
                            attachments=attachments,
                        )
                    )
                    LogEntry.objects.log_create(
                        instance=policy,
                        action=LogEntry.Action.UPDATE,
                        changes={
                            "message": [
                                "",
                                f"Sent documents to {user.email}. Subject: {form.cleaned_data['subject']}",
                            ]
                        },
                        actor=request.user,
                    )
                    self.message_user(
                        request, f"Email sent to {user.email}", messages.SUCCESS
                    )
                    return redirect("admin:policies_policy_change", policy_id)
                except Exception as e:
                    self.message_user(
                        request, f"Failed to send email: {str(e)}", messages.ERROR
                    )
        else:
            form = SendDocumentsForm()

        context = {
            "form": form,
            "policy": policy,
            "user": user,
            "opts": self.model._meta,
            "title": f"Send Documents - {policy.policy_number}",
        }
        return render(request, "admin/policies/policy/send_documents.html", context)

    def download_coi_view(self, request, policy_id):
        policy = Policy.objects.select_related("quote").get(id=policy_id)
        policies = list(Policy.objects.filter(quote=policy.quote))
        coi_number = policy.coi_number or policy.policy_number

        pdf_bytes = DocumentsGeneratorService.generate_coi_for_policies(
            policies, coi_number
        )
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="COI-{coi_number}.pdf"'
            )
            return response

        self.message_user(request, "Failed to generate COI", messages.ERROR)
        return redirect("admin:policies_policy_change", policy_id)

    def download_cgl_policy_view(self, request, policy_id):
        policy = Policy.objects.get(id=policy_id)
        all_policies = list(Policy.objects.filter(quote=policy.quote))

        pdf_bytes = DocumentsGeneratorService.generate_cgl_policy_for_policy(
            policy, all_policies
        )
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="CGL-Policy-{policy.policy_number}.pdf"'
            )
            return response

        self.message_user(
            request,
            "Failed to generate CGL Policy (no CGL/HNOA coverages found)",
            messages.ERROR,
        )
        return redirect("admin:policies_policy_change", policy_id)

    def download_tech_policy_view(self, request, policy_id):
        policy = Policy.objects.get(id=policy_id)
        all_policies = list(Policy.objects.filter(quote_id=policy.quote_id))

        pdf_bytes = DocumentsGeneratorService.generate_tech_policy_for_policy(
            policy, all_policies
        )
        if pdf_bytes:
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = (
                f'attachment; filename="Tech-Policy-{policy.policy_number}.pdf"'
            )
            return response

        self.message_user(
            request,
            "Failed to generate Tech Policy (no tech coverages found)",
            messages.ERROR,
        )
        return redirect("admin:policies_policy_change", policy_id)

    def apply_promo_code_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related("quote").get(id=policy_id)

        if policy.is_brokered:
            self.message_user(
                request,
                "Cannot apply promo codes to brokered policies.",
                messages.ERROR,
            )
            return redirect("admin:policies_policy_change", policy_id)

        if policy.promo_code:
            self.message_user(
                request,
                "Policy already has a promo code. Remove it first.",
                messages.ERROR,
            )
            return redirect("admin:policies_policy_change", policy_id)

        if request.method == "POST":
            form = ApplyPromoCodeForm(request.POST)
            if form.is_valid():
                code = form.cleaned_data["promo_code"]
                promo = StripeService.get_promotion_code(code)
                if not promo:
                    self.message_user(
                        request,
                        f"Promo code '{code}' not found or inactive in Stripe.",
                        messages.ERROR,
                    )
                    return redirect("admin:policies_policy_apply_promo", policy_id)

                try:
                    result = PolicyService.apply_promo_to_policy(policy, promo)
                    LogEntry.objects.log_create(
                        instance=policy,
                        action=LogEntry.Action.UPDATE,
                        changes={
                            "message": [
                                "",
                                f"Applied promo code: {form.cleaned_data['promo_code']}",
                            ]
                        },
                        actor=request.user,
                    )
                    msg = f"Promo '{code}' applied. Premium: ${result['old_premium']} → ${result['new_premium']} (delta: ${result['delta']})"
                    self.message_user(request, msg, messages.SUCCESS)
                    return redirect("admin:policies_policy_change", policy_id)
                except (ValueError, Exception) as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = ApplyPromoCodeForm()

        context = {
            "form": form,
            "policy": policy,
            "opts": self.model._meta,
            "title": f"Apply Promo Code - {policy.policy_number}",
        }
        return render(request, "admin/policies/policy/apply_promo_code.html", context)

    def _get_limit_choices(self, coverage_type):
        definition = get_definition(coverage_type)
        if not definition:
            return {}

        def fmt(val):
            return (str(val), f"${val:,}")

        return {
            "aggregate_limits": [
                fmt(o.value)
                for o in definition.limits_retentions.aggregate_limits
                if o.value <= MAX_SELF_SERVE_LIMIT
            ],
            "per_occurrence_limits": [
                fmt(o.value)
                for o in definition.limits_retentions.per_occurrence_limits
                if o.value <= MAX_SELF_SERVE_LIMIT
            ],
            "retentions": [
                fmt(o.value) for o in definition.limits_retentions.retentions
            ],
        }

    def _calculate_endorsement_premium(self, policy, new_limits=None):
        quote = policy.quote
        coverage = policy.coverage_type
        definition = get_definition(coverage)
        if not definition:
            return None

        questionnaire_data = quote.coverage_data.get(coverage) or {}
        try:
            validated = validate_questionnaire(coverage, questionnaire_data)
            questionnaire = validated.model_dump()
        except Exception:
            questionnaire = questionnaire_data

        stored_ai = (quote.initial_ai_classifications or {}).get(coverage, {})
        if stored_ai:
            for ai_key, value in stored_ai.items():
                if ai_key in ("do_industry_group", "epl_industry_group"):
                    questionnaire["industry_group"] = value
                elif ai_key == "tech_eo_hazard_class":
                    questionnaire["hazardClass"] = value
                elif ai_key == "cgl_hazard_class":
                    questionnaire["primary_operations_hazard"] = value
                elif ai_key == "products_operations_multiplier":
                    questionnaire["products_operations_multiplier"] = value

        limits = new_limits or policy.limits_retentions or {}
        aggregate_limit = limits.get("aggregate_limit") or 1_000_000
        per_occurrence_limit = limits.get("per_occurrence_limit") or aggregate_limit
        retention = (
            limits.get("retention") or definition.limits_retentions.retentions[0].value
        )

        override = quote.underwriter_overrides.filter(coverage=coverage).first()

        context = CalculationContext(
            questionnaire=questionnaire,
            revenue=quote.company.last_12_months_revenue,
            limit=aggregate_limit,
            retention=retention,
            per_occurrence_limit=per_occurrence_limit,
            employee_count=questionnaire.get("total_employees_us") or 0,
            driver_count=questionnaire.get("num_employees_driving") or 0,
            state=quote.company.business_address.state
            if quote.company.business_address
            else "",
            business_description=quote.company.business_description or "",
        )

        result = RatingService.calculate(
            definition,
            context,
            bypass_review=True,
            underwriter_multiplier=float(override.multiplier) if override else 1.0,
        )
        if not result.success:
            return None
        premium = Decimal(str(result.premium))
        if policy.discount_percentage:
            premium = premium * (1 - policy.discount_percentage / 100)
        if policy.billing_frequency == "monthly":
            premium = RatingService.apply_monthly_surcharge(premium)
        return round(float(premium), 2)

    def endorse_modify_limits_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related(
            "quote", "quote__company", "quote__company__business_address"
        ).get(id=policy_id)

        if policy.status != "active" or policy.is_brokered:
            self.message_user(request, "Cannot endorse this policy.", messages.ERROR)
            return redirect("admin:policies_policy_change", policy_id)

        limit_choices = self._get_limit_choices(policy.coverage_type)
        limits = policy.limits_retentions or {}
        initial = {
            "aggregate_limit": str(
                limits.get("aggregateLimit") or limits.get("aggregate_limit") or 0
            ),
            "per_occurrence_limit": str(
                limits.get("perOccurrenceLimit")
                or limits.get("per_occurrence_limit")
                or 0
            ),
            "retention": str(limits.get("retention") or 0),
        }

        calculated_premium = None
        carrier_switch_warning = False

        if request.method == "POST":
            is_calculate = "calculate" in request.POST
            form = ModifyLimitsForm(request.POST, limit_choices=limit_choices)
            if is_calculate:
                form.fields["reason"].required = False
                form.fields["new_premium"].required = False
            if form.is_valid():
                new_limits = {
                    "aggregate_limit": int(form.cleaned_data["aggregate_limit"]),
                    "per_occurrence_limit": int(
                        form.cleaned_data["per_occurrence_limit"]
                    ),
                    "retention": int(form.cleaned_data["retention"]),
                }

                aggregate_limit = new_limits["aggregate_limit"]
                carrier_switch_warning = aggregate_limit > NTIC_LIMIT_THRESHOLD

                calculated_premium = self._calculate_endorsement_premium(
                    policy, new_limits
                )

                if is_calculate:
                    form = ModifyLimitsForm(
                        initial={**request.POST.dict()},
                        limit_choices=limit_choices,
                    )
                else:
                    new_premium = form.cleaned_data.get("new_premium")
                    if not new_premium and calculated_premium:
                        new_premium = calculated_premium
                    elif not new_premium:
                        self.message_user(
                            request,
                            "Could not auto-calculate premium. Please enter it manually.",
                            messages.ERROR,
                        )
                        context = {
                            "form": form,
                            "policy": policy,
                            "calculated_premium": calculated_premium,
                            "carrier_switch_warning": carrier_switch_warning,
                            "opts": self.model._meta,
                            "title": f"Modify Limits - {policy.policy_number}",
                        }
                        return render(
                            request,
                            "admin/policies/policy/endorse_modify_limits.html",
                            context,
                        )

                    reason = form.cleaned_data["reason"]

                    try:
                        result = PolicyService.endorse_modify_limits(
                            policy, new_limits, Decimal(str(new_premium)), reason
                        )
                        LogEntry.objects.log_create(
                            instance=policy,
                            action=LogEntry.Action.UPDATE,
                            changes={
                                "message": [
                                    "",
                                    f"Modified limits. Reason: {form.cleaned_data['reason']}",
                                ]
                            },
                            actor=request.user,
                        )
                        msg = (
                            f"Limits modified. Premium: ${result['old_premium']} → ${result['new_premium']} "
                            f"(full-term delta: ${result['full_term_delta']}, prorated: ${result['prorated_delta']})"
                        )
                        if result.get("invoice_sent"):
                            msg += " - No payment method on file, an invoice has been emailed to the customer."
                        self.message_user(request, msg, messages.SUCCESS)
                        return redirect("admin:policies_policy_change", policy_id)
                    except (ValueError, Exception) as e:
                        self.message_user(request, str(e), messages.ERROR)
        else:
            form = ModifyLimitsForm(initial=initial, limit_choices=limit_choices)

        context = {
            "form": form,
            "policy": policy,
            "calculated_premium": calculated_premium,
            "carrier_switch_warning": carrier_switch_warning,
            "opts": self.model._meta,
            "title": f"Modify Limits - {policy.policy_number}",
        }
        return render(
            request, "admin/policies/policy/endorse_modify_limits.html", context
        )

    def endorse_add_coverage_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related("quote").get(id=policy_id)

        if policy.status != "active":
            self.message_user(
                request, "Can only add coverage to active policies.", messages.ERROR
            )
            return redirect("admin:policies_policy_change", policy_id)

        existing_coverages = set(
            Policy.objects.filter(
                coi_number=policy.coi_number, status="active"
            ).values_list("coverage_type", flat=True)
        )
        available = [
            (c, COVERAGE_DISPLAY_NAMES.get(c, c))
            for c in ALL_COVERAGES
            if c not in existing_coverages
        ]
        brokered_choices = [
            (pt_val, f"[Brokered] {pt_label}")
            for pt_val, pt_label in CustomProduct.PRODUCT_TYPES
            if pt_val not in existing_coverages
        ]
        if brokered_choices:
            available = available + brokered_choices

        if not available:
            self.message_user(
                request,
                "All coverage types are already present in this COI group.",
                messages.WARNING,
            )
            return redirect("admin:policies_policy_change", policy_id)

        if request.method == "POST":
            form = AddCoverageForm(request.POST, coverage_choices=available)
            if form.is_valid():
                new_limits = {
                    "aggregate_limit": form.cleaned_data["aggregate_limit"],
                    "per_occurrence_limit": form.cleaned_data["per_occurrence_limit"],
                    "retention": form.cleaned_data["retention"],
                }
                try:
                    result = PolicyService.endorse_add_coverage(
                        policy,
                        form.cleaned_data["coverage_type"],
                        new_limits,
                        Decimal(str(form.cleaned_data["premium"])),
                        form.cleaned_data["reason"],
                        is_brokered=form.cleaned_data.get("is_brokered", False),
                        carrier=form.cleaned_data.get("carrier", ""),
                    )
                    LogEntry.objects.log_create(
                        instance=policy,
                        action=LogEntry.Action.UPDATE,
                        changes={
                            "message": [
                                "",
                                f"Added coverage: {form.cleaned_data['coverage_type']}. Reason: {form.cleaned_data['reason']}",
                            ]
                        },
                        actor=request.user,
                    )
                    msg = (
                        f"Coverage added: {COVERAGE_DISPLAY_NAMES.get(form.cleaned_data['coverage_type'], form.cleaned_data['coverage_type'])}. "
                        f"Full-term premium: ${result['full_term_premium']}, prorated: ${result['prorated_premium']}"
                    )
                    if result.get("invoice_sent"):
                        msg += " - No payment method on file, an invoice has been emailed to the customer."
                    self.message_user(request, msg, messages.SUCCESS)
                    return redirect(
                        "admin:policies_policy_change", result["new_policy"].id
                    )
                except (ValueError, Exception) as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = AddCoverageForm(coverage_choices=available)

        sibling_policies = Policy.objects.filter(
            coi_number=policy.coi_number, status="active"
        ).values_list("coverage_type", "premium")

        context = {
            "form": form,
            "policy": policy,
            "sibling_policies": list(sibling_policies),
            "coverage_display_names": COVERAGE_DISPLAY_NAMES,
            "opts": self.model._meta,
            "title": f"Add Coverage - COI {policy.coi_number}",
        }
        return render(
            request, "admin/policies/policy/endorse_add_coverage.html", context
        )

    def endorse_remove_coverage_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related("quote").get(id=policy_id)

        if policy.status != "active" or policy.is_brokered:
            self.message_user(request, "Cannot remove this coverage.", messages.ERROR)
            return redirect("admin:policies_policy_change", policy_id)

        sibling_count = (
            Policy.objects.filter(coi_number=policy.coi_number, status="active")
            .exclude(pk=policy.pk)
            .count()
        )

        if sibling_count == 0:
            self.message_user(
                request,
                "Cannot remove the last coverage in a COI group.",
                messages.ERROR,
            )
            return redirect("admin:policies_policy_change", policy_id)

        proration_factor = PolicyService._calculate_proration_factor(policy)
        estimated_refund = (policy.premium * proration_factor).quantize(Decimal("0.01"))

        if request.method == "POST":
            form = RemoveCoverageForm(request.POST)
            if form.is_valid():
                try:
                    result = PolicyService.endorse_remove_coverage(
                        policy, form.cleaned_data["reason"]
                    )
                    LogEntry.objects.log_create(
                        instance=policy,
                        action=LogEntry.Action.UPDATE,
                        changes={
                            "message": [
                                "",
                                f"Removed coverage: {policy.coverage_type}. Reason: {form.cleaned_data['reason']}",
                            ]
                        },
                        actor=request.user,
                    )
                    msg = f"Coverage removed: {COVERAGE_DISPLAY_NAMES.get(policy.coverage_type, policy.coverage_type)}. Refund: ${result['refund_amount']}"
                    self.message_user(request, msg, messages.SUCCESS)
                    return redirect("admin:policies_policy_change", policy_id)
                except (ValueError, Exception) as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = RemoveCoverageForm()

        context = {
            "form": form,
            "policy": policy,
            "estimated_refund": estimated_refund,
            "proration_factor": proration_factor,
            "opts": self.model._meta,
            "title": f"Remove Coverage - {policy.policy_number}",
        }
        return render(
            request, "admin/policies/policy/endorse_remove_coverage.html", context
        )

    def cancel_policy_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related("quote").get(id=policy_id)

        if policy.status != "active":
            self.message_user(
                request, "Can only cancel active policies.", messages.ERROR
            )
            return redirect("admin:policies_policy_change", policy_id)

        proration_factor = PolicyService._calculate_proration_factor(policy)
        estimated_refund = (policy.premium * proration_factor).quantize(Decimal("0.01"))

        if request.method == "POST":
            form = CancelPolicyForm(request.POST)
            if form.is_valid():
                try:
                    result = PolicyService.cancel_policy(
                        policy, form.cleaned_data["reason"]
                    )
                    LogEntry.objects.log_create(
                        instance=policy,
                        action=LogEntry.Action.UPDATE,
                        changes={
                            "message": [
                                "",
                                f"Cancelled policy. Refund: ${result['refund_amount']}. Reason: {form.cleaned_data['reason']}",
                            ]
                        },
                        actor=request.user,
                    )
                    msg = f"Policy cancelled: {policy.policy_number}. Refund: ${result['refund_amount']}"
                    self.message_user(request, msg, messages.SUCCESS)
                    return redirect("admin:policies_policy_change", policy_id)
                except (ValueError, Exception) as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = CancelPolicyForm()

        context = {
            "form": form,
            "policy": policy,
            "estimated_refund": estimated_refund,
            "proration_factor": proration_factor,
            "opts": self.model._meta,
            "title": f"Cancel Policy - {policy.policy_number}",
        }
        return render(request, "admin/policies/policy/cancel_policy.html", context)

    def reactivate_policy_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related(
            "quote", "quote__company", "quote__company__business_address"
        ).get(id=policy_id)

        if policy.status != "cancelled":
            self.message_user(
                request, "Can only reactivate cancelled policies.", messages.ERROR
            )
            return redirect("admin:policies_policy_change", policy_id)

        if policy.billing_frequency != "monthly":
            self.message_user(
                request, "Can only reactivate monthly-billed policies.", messages.ERROR
            )
            return redirect("admin:policies_policy_change", policy_id)

        sibling_policies = (
            list(
                Policy.objects.select_related(
                    "quote", "quote__company", "quote__company__business_address"
                )
                .filter(coi_number=policy.coi_number, status="cancelled")
                .exclude(pk=policy.pk)
            )
            if policy.coi_number
            else []
        )

        restored_expiration = policy.effective_date + timedelta(days=365)

        if request.method == "POST":
            form = ReactivatePolicyForm(request.POST)
            if form.is_valid():
                reactivation_date = form.cleaned_data["reactivation_date"]

                selected_ids = request.POST.getlist("sibling_policies")
                selected_siblings = [
                    p for p in sibling_policies if str(p.pk) in selected_ids
                ]
                all_policies = [policy] + selected_siblings

                try:
                    result = PolicyService.reactivate_policy(
                        all_policies,
                        reactivation_date,
                        request.user.get_username(),
                    )
                    for p in all_policies:
                        LogEntry.objects.log_create(
                            instance=p,
                            action=LogEntry.Action.UPDATE,
                            changes={
                                "message": [
                                    "",
                                    f"Reactivated policy. Gap premium: ${result['gap_premium']}",
                                ]
                            },
                            actor=request.user,
                        )
                    policy_numbers = ", ".join(p.policy_number for p in all_policies)
                    gap_msg = (
                        f" Gap premium: ${result['gap_premium']}"
                        if result["gap_premium"] > 0
                        else ""
                    )
                    self.message_user(
                        request,
                        f"Policies reactivated: {policy_numbers}.{gap_msg}",
                        messages.SUCCESS,
                    )
                    return redirect("admin:policies_policy_change", policy_id)
                except Exception as e:
                    self.message_user(request, str(e), messages.ERROR)
        else:
            form = ReactivatePolicyForm(initial={"reactivation_date": date.today()})

        gap_days = 0
        gap_premium = Decimal("0")

        context = {
            "form": form,
            "policy": policy,
            "sibling_policies": sibling_policies,
            "restored_expiration": restored_expiration,
            "gap_days": gap_days,
            "gap_premium": gap_premium,
            "opts": self.model._meta,
            "title": f"Reactivate Policy - {policy.policy_number}",
        }
        return render(request, "admin/policies/policy/reactivate_policy.html", context)

    def endorse_backdate_policy_view(self, request, policy_id):
        if deny := self._require_full_access(request, policy_id):
            return deny
        policy = Policy.objects.select_related(
            "quote", "quote__company", "quote__company__business_address"
        ).get(id=policy_id)

        if policy.status != "active":
            self.message_user(
                request, "Can only backdate active policies.", messages.ERROR
            )
            return redirect("admin:policies_policy_change", policy_id)

        preview = None

        if request.method == "POST":
            is_preview = "preview" in request.POST
            form = BackdatePolicyForm(request.POST)
            if is_preview:
                form.fields["reason"].required = False
            if form.is_valid():
                new_effective_date = form.cleaned_data["new_effective_date"]

                if new_effective_date >= policy.effective_date:
                    self.message_user(
                        request,
                        "New effective date must be before the current effective date.",
                        messages.ERROR,
                    )
                elif (policy.effective_date - new_effective_date).days > 30:
                    self.message_user(
                        request, "Cannot backdate more than 30 days.", messages.ERROR
                    )
                else:
                    old_effective = policy.effective_date
                    old_total_days = (policy.expiration_date - old_effective).days
                    new_total_days = (policy.expiration_date - new_effective_date).days
                    extra_days = (old_effective - new_effective_date).days
                    new_premium = (
                        policy.premium
                        * Decimal(new_total_days)
                        / Decimal(old_total_days)
                    ).quantize(Decimal("0.01"))
                    premium_delta = new_premium - policy.premium

                    preview = {
                        "new_effective_date": new_effective_date,
                        "extra_days": extra_days,
                        "new_premium": new_premium,
                        "premium_delta": premium_delta,
                    }

                    if is_preview:
                        form = BackdatePolicyForm(
                            initial={
                                "new_effective_date": new_effective_date.isoformat(),
                            }
                        )
                    else:
                        reason = form.cleaned_data["reason"]
                        try:
                            result = PolicyService.endorse_backdate_policy(
                                policy, new_effective_date, reason
                            )
                            LogEntry.objects.log_create(
                                instance=policy,
                                action=LogEntry.Action.UPDATE,
                                changes={
                                    "message": [
                                        "",
                                        f"Backdated policy to {form.cleaned_data['new_effective_date']}. Reason: {form.cleaned_data['reason']}",
                                    ]
                                },
                                actor=request.user,
                            )
                            msg = (
                                f"Policy backdated. Effective: {result['old_effective_date']} → {result['new_effective_date']} "
                                f"({result['extra_days']} extra days). Premium: ${result['old_premium']} → ${result['new_premium']} "
                                f"(+${result['premium_delta']})"
                            )
                            if result.get("invoice_sent"):
                                msg += " - No payment method on file, an invoice has been emailed to the customer."
                            self.message_user(request, msg, messages.SUCCESS)
                            return redirect("admin:policies_policy_change", policy_id)
                        except (ValueError, Exception) as e:
                            self.message_user(request, str(e), messages.ERROR)
        else:
            form = BackdatePolicyForm()

        context = {
            "form": form,
            "policy": policy,
            "preview": preview,
            "opts": self.model._meta,
            "title": f"Backdate Policy - {policy.policy_number}",
        }
        return render(
            request, "admin/policies/policy/endorse_backdate_policy.html", context
        )

    def export_premium_report_csv(self, request):
        from django.db import connection

        status_filter = request.GET.get("status", "active")
        status_clause = "AND status = %s" if status_filter != "all" else ""
        params = [status_filter] if status_filter != "all" else []

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="premium-report-{status_filter}.csv"'
        )

        writer = csv.writer(response)

        writer.writerow(["RRG (Direct Written)"])
        writer.writerow(["Coverage Type", "Count", "Premium"])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT coverage_type, COUNT(*) as policy_count, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = false {status_clause}
                GROUP BY coverage_type
                ORDER BY total_premium DESC
            """,
                params,
            )
            rrg_premiums = cursor.fetchall()

            for row in rrg_premiums:
                writer.writerow([row[0] or "Unknown", row[1], f"{row[2]:.2f}"])

            cursor.execute(
                f"""
                SELECT COUNT(*) as total_policies, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = false {status_clause}
            """,
                params,
            )
            rrg_total = cursor.fetchone()
            writer.writerow(["Total", rrg_total[0], f"{rrg_total[1]:.2f}"])

            writer.writerow([])

            writer.writerow(["Brokered"])
            writer.writerow(["Coverage Type", "Carrier", "Count", "Premium"])

            cursor.execute(
                f"""
                SELECT coverage_type, carrier, COUNT(*) as policy_count, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = true {status_clause}
                GROUP BY coverage_type, carrier
                ORDER BY total_premium DESC
            """,
                params,
            )
            brokered_premiums = cursor.fetchall()

            for row in brokered_premiums:
                writer.writerow(
                    [row[0] or "Unknown", row[1] or "Unknown", row[2], f"{row[3]:.2f}"]
                )

            cursor.execute(
                f"""
                SELECT COUNT(*) as total_policies, COALESCE(SUM(premium), 0) as total_premium
                FROM policies
                WHERE is_brokered = true {status_clause}
            """,
                params,
            )
            brokered_total = cursor.fetchone()
            writer.writerow(
                ["Total", "", brokered_total[0], f"{brokered_total[1]:.2f}"]
            )

            writer.writerow([])

            writer.writerow(["Grand Total"])
            grand_total_rrg = rrg_total[1] or 0
            grand_total_brokered = brokered_total[1] or 0
            writer.writerow(["RRG", f"{grand_total_rrg:.2f}"])
            writer.writerow(["Brokered", f"{grand_total_brokered:.2f}"])
            writer.writerow(["Total", f"{grand_total_rrg + grand_total_brokered:.2f}"])

        return response

    def export_payment_status_csv(self, request):
        status_filter = request.GET.get("status", "active")
        billing_filter = request.GET.get("billing", "all")

        policies = (
            Policy.objects.select_related("quote")
            .annotate(
                total_charges=Coalesce(
                    Sum("payments__amount", filter=Q(payments__amount__gt=0)),
                    Value(0),
                    output_field=DecimalField(),
                ),
                total_refunds=Coalesce(
                    Sum(
                        Case(When(payments__amount__lt=0, then=-F("payments__amount"))),
                        output_field=DecimalField(),
                    ),
                    Value(0),
                    output_field=DecimalField(),
                ),
            )
            .annotate(
                net_collected=F("total_charges") - F("total_refunds"),
            )
        )

        if status_filter and status_filter != "all":
            policies = policies.filter(status=status_filter)

        if billing_filter and billing_filter != "all":
            policies = policies.filter(billing_frequency=billing_filter)

        policies = policies.order_by("-created_at")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="payment-status-{status_filter}-{billing_filter}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Policy Number",
                "Coverage",
                "Billing",
                "Premium",
                "Promo Code",
                "Charges",
                "Refunds",
                "Net Collected",
            ]
        )

        total_premium = 0
        total_charges = 0
        total_refunds = 0

        for policy in policies:
            total_premium += policy.premium
            total_charges += policy.total_charges
            total_refunds += policy.total_refunds
            writer.writerow(
                [
                    policy.policy_number,
                    policy.coverage_type,
                    policy.billing_frequency,
                    f"{policy.premium:.2f}",
                    policy.promo_code or "",
                    f"{policy.total_charges:.2f}",
                    f"{policy.total_refunds:.2f}",
                    f"{policy.net_collected:.2f}",
                ]
            )

        total_net = total_charges - total_refunds
        writer.writerow([])
        writer.writerow(
            [
                "Grand Total",
                "",
                "",
                f"{total_premium:.2f}",
                "",
                f"{total_charges:.2f}",
                f"{total_refunds:.2f}",
                f"{total_net:.2f}",
            ]
        )

        return response

    # ── Renewal Pipeline View (V3 #20) ─────────────────────────────────

    def renewal_pipeline_view(self, request):
        """
        Kanban-style renewal pipeline view.

        Shows policies grouped by renewal_status in columns:
          not_due → offered → quoted → renewed / lapsed

        Also handles POST actions to advance a policy's renewal status and
        trigger automated emails per stage.
        """
        from emails.service import EmailService
        from emails.schemas import SendEmailInput

        if request.method == "POST":
            action = request.POST.get("action")
            policy_id = request.POST.get("policy_id")
            if action and policy_id:
                try:
                    policy = Policy.objects.select_related(
                        "quote__user", "quote__company"
                    ).get(pk=policy_id)
                    old_status = policy.renewal_status

                    STATUS_TRANSITIONS = {
                        "mark_offered": "offered",
                        "mark_quoted": "quoted",
                        "mark_renewed": "renewed",
                        "mark_lapsed": "non_renewed",
                    }

                    new_status = STATUS_TRANSITIONS.get(action)
                    if new_status:
                        policy.renewal_status = new_status
                        policy.save(update_fields=["renewal_status"])

                        # Trigger email automation per stage
                        user_email = policy.quote.user.email
                        company_name = (
                            policy.quote.company.entity_legal_name or "Valued Customer"
                        )

                        if new_status == "offered" and old_status == "not_due":
                            try:
                                EmailService.send_email(
                                    SendEmailInput(
                                        to=user_email,
                                        subject=f"Your Policy Renewal Offer — {policy.policy_number}",
                                        html_content=(
                                            f"<p>Dear {company_name},</p>"
                                            f"<p>Your policy <strong>{policy.policy_number}</strong> is coming up for renewal. "
                                            f"We have prepared a renewal offer for you. Please log in to review and accept.</p>"
                                            f"<p>Expiration date: {policy.expiration_date}</p>"
                                        ),
                                    )
                                )
                            except Exception:
                                pass  # email failure should not block status update

                        elif new_status == "quoted":
                            try:
                                EmailService.send_email(
                                    SendEmailInput(
                                        to=user_email,
                                        subject=f"Renewal Quote Ready — {policy.policy_number}",
                                        html_content=(
                                            f"<p>Dear {company_name},</p>"
                                            f"<p>Your renewal quote for policy <strong>{policy.policy_number}</strong> is ready. "
                                            f"Please log in to review pricing and complete your renewal.</p>"
                                        ),
                                    )
                                )
                            except Exception:
                                pass

                        elif new_status == "renewed":
                            try:
                                EmailService.send_email(
                                    SendEmailInput(
                                        to=user_email,
                                        subject=f"Policy Renewed — {policy.policy_number}",
                                        html_content=(
                                            f"<p>Dear {company_name},</p>"
                                            f"<p>Your policy <strong>{policy.policy_number}</strong> has been successfully renewed. "
                                            f"Thank you for continuing with Corgi.</p>"
                                        ),
                                    )
                                )
                            except Exception:
                                pass

                        elif new_status == "non_renewed":
                            try:
                                EmailService.send_email(
                                    SendEmailInput(
                                        to=user_email,
                                        subject=f"Policy Not Renewed — {policy.policy_number}",
                                        html_content=(
                                            f"<p>Dear {company_name},</p>"
                                            f"<p>We regret to inform you that your policy <strong>{policy.policy_number}</strong> "
                                            f"will not be renewed. If you have questions, please contact us.</p>"
                                        ),
                                    )
                                )
                            except Exception:
                                pass

                        self.message_user(
                            request,
                            f"Policy {policy.policy_number} moved to {new_status}.",
                            messages.SUCCESS,
                        )
                    else:
                        self.message_user(request, "Unknown action.", messages.ERROR)
                except Policy.DoesNotExist:
                    self.message_user(request, "Policy not found.", messages.ERROR)

            return redirect("admin:policies_policy_renewal_pipeline")

        today = date.today()
        ninety_days = today + timedelta(days=90)

        # Policies expiring within 90 days (most relevant for pipeline)
        base_qs = (
            Policy.objects.filter(
                status="active",
                expiration_date__lte=ninety_days,
            )
            .select_related("quote__company", "quote__user")
            .order_by("expiration_date")
        )

        # Also include recently lapsed / renewed for visibility
        lapsed_qs = (
            Policy.objects.filter(
                renewal_status="non_renewed",
            )
            .select_related("quote__company", "quote__user")
            .order_by("-expiration_date")[:20]
        )

        renewed_qs = (
            Policy.objects.filter(
                renewal_status="renewed",
            )
            .select_related("quote__company", "quote__user")
            .order_by("-expiration_date")[:20]
        )

        pipeline = {
            "not_due": base_qs.filter(renewal_status="not_due"),
            "offered": base_qs.filter(renewal_status="offered"),
            "quoted": base_qs.filter(renewal_status="quoted"),
            "renewed": renewed_qs,
            "lapsed": lapsed_qs,
        }

        context = {
            **self.admin_site.each_context(request),
            "pipeline": pipeline,
            "today": today,
            "opts": self.model._meta,
            "title": "Renewal Pipeline",
        }
        return render(request, "admin/policies/policy/renewal_pipeline.html", context)


# ── PolicyRenewal ────────────────────────────────────────────────────────


@admin.register(PolicyRenewal)
class PolicyRenewalAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_link_header",
        "status_colored",
        "new_quote_link",
        "offered_at",
        "expires_at",
        "accepted_at",
        "created_at",
    ]
    list_display_links = ["policy_link_header"]
    list_filter = ["status", "created_at"]
    search_fields = ["policy__policy_number", "new_quote__quote_number"]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]
    list_per_page = 25
    date_hierarchy = "created_at"
    autocomplete_fields = ["policy", "new_quote"]

    fieldsets = (
        (
            None,
            {
                "fields": ("policy", "new_quote", "status"),
            },
        ),
        (
            "Dates",
            {
                "classes": ["tab"],
                "fields": ("offered_at", "expires_at", "accepted_at"),
            },
        ),
        (
            "Notes",
            {
                "classes": ["tab"],
                "fields": ("notes",),
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

    @display(description="Policy", header=True)
    def policy_link_header(self, obj):
        return [obj.policy.policy_number, ""]

    @admin.display(description="New Quote")
    def new_quote_link(self, obj):
        if obj.new_quote:
            url = reverse("admin:quotes_quote_change", args=[obj.new_quote_id])
            return format_html('<a href="{}">{}</a>', url, obj.new_quote.quote_number)
        return "-"

    @display(
        description="Status",
        ordering="status",
        label={
            "pending": "warning",
            "accepted": "success",
            "declined": "danger",
            "expired": "info",
        },
    )
    def status_colored(self, obj):
        return obj.status, obj.get_status_display()


@admin.register(PolicyExcessLayer)
class PolicyExcessLayerAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_link",
        "primary_carrier",
        "primary_limit_display",
        "excess_carrier",
        "excess_limit_display",
        "total_premium_display",
        "created_at",
    ]
    list_display_links = ["policy_link"]
    search_fields = [
        "policy__policy_number",
        "primary_carrier",
        "primary_policy_number",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "total_premium_display",
        "total_limit_display",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Primary Layer",
            {
                "fields": (
                    "policy",
                    "primary_carrier",
                    "primary_carrier_naic",
                    "primary_policy_number",
                    "primary_limit",
                    "primary_retention",
                    "primary_premium",
                ),
            },
        ),
        (
            "Excess / RRG Layer",
            {
                "fields": (
                    "excess_carrier",
                    "excess_carrier_naic",
                    "excess_attachment_point",
                    "excess_limit",
                    "excess_premium",
                ),
            },
        ),
        (
            "Summary",
            {
                "fields": ("total_premium_display", "total_limit_display", "notes"),
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

    @display(description="Policy")
    def policy_link(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    @display(description="Primary Limit")
    def primary_limit_display(self, obj):
        return "${:,}".format(obj.primary_limit)

    @display(description="Excess Limit")
    def excess_limit_display(self, obj):
        return "${:,} xs ${:,}".format(obj.excess_limit, obj.excess_attachment_point)

    @display(description="Total Premium")
    def total_premium_display(self, obj):
        return "${:,.2f}".format(obj.total_premium)

    total_premium_display.short_description = "Total Premium"

    @display(description="Total Limit")
    def total_limit_display(self, obj):
        return "${:,}".format(obj.total_limit)

    total_limit_display.short_description = "Total Limit"


@admin.register(SurplusLinesFiling)
class SurplusLinesFilingAdmin(ReadOnlyAdminMixin, UnfoldModelAdmin):
    list_display = [
        "policy_link",
        "filing_state",
        "status_badge",
        "filing_deadline",
        "overdue_icon",
        "surplus_lines_tax_amount",
        "filed_at",
        "created_at",
    ]
    list_display_links = ["policy_link"]
    list_filter = ["status", "filing_state", "filing_deadline"]
    search_fields = ["policy__policy_number", "stamping_reference", "filing_state"]
    readonly_fields = ["created_at", "updated_at", "is_overdue_display"]
    ordering = ["filing_deadline"]
    date_hierarchy = "filing_deadline"

    fieldsets = (
        (
            "Policy & State",
            {
                "fields": ("policy", "filing_state", "status", "stamping_office"),
            },
        ),
        (
            "Tax Calculation",
            {
                "fields": (
                    "surplus_lines_tax_rate",
                    "surplus_lines_tax_amount",
                    "stamping_fee",
                ),
            },
        ),
        (
            "Diligent Search",
            {
                "fields": (
                    "diligent_search_completed_at",
                    "admitted_carriers_approached",
                    "diligent_search_document_key",
                ),
            },
        ),
        (
            "Filing Timeline",
            {
                "fields": (
                    "binding_date",
                    "filing_deadline",
                    "filed_at",
                    "stamped_at",
                    "stamping_reference",
                    "is_overdue_display",
                ),
            },
        ),
        (
            "Notes",
            {
                "fields": ("notes",),
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

    @display(description="Policy")
    def policy_link(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    @display(
        description="Status",
        ordering="status",
        label={
            "pending": "warning",
            "diligent_search_complete": "info",
            "filed": "success",
            "stamped": "success",
            "overdue": "danger",
            "exempt": "info",
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    @display(description="Overdue", boolean=True)
    def overdue_icon(self, obj):
        return obj.is_overdue

    @display(description="Is Overdue")
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span style="color:#dc2626;font-weight:600;">YES - past deadline</span>'
            )
        return "No"


# ── Coverage Modification Requests (V3 #9) ────────────────────────────────────

from policies.models import CoverageModificationRequest  # noqa: E402


@admin.register(CoverageModificationRequest)
class CoverageModificationRequestAdmin(UnfoldModelAdmin):
    """Admin for reviewing and actioning coverage modification requests."""

    list_display = (
        "id",
        "policy_link",
        "status_badge",
        "requested_by",
        "reviewed_by",
        "created_at",
        "reviewed_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("policy__policy_number", "reason", "requested_by__email")
    readonly_fields = (
        "created_at",
        "updated_at",
        "reviewed_at",
        "requested_by",
        "policy_link_ro",
    )
    ordering = ("-created_at",)

    fieldsets = (
        (
            "Request Details",
            {
                "fields": (
                    "policy_link_ro",
                    "requested_by",
                    "reason",
                    "requested_changes",
                ),
            },
        ),
        (
            "Review",
            {
                "fields": ("status", "reviewed_by", "reviewed_at", "reviewer_notes"),
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

    @display(description="Policy")
    def policy_link(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    @display(description="Policy")
    def policy_link_ro(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    @display(
        description="Status",
        ordering="status",
        label={
            "pending": "warning",
            "approved": "success",
            "denied": "danger",
        },
    )
    def status_badge(self, obj):
        return obj.status, obj.get_status_display()

    def save_model(self, request, obj, form, change):
        """Auto-stamp reviewed_by and reviewed_at when status changes from pending."""
        if change:
            original = CoverageModificationRequest.objects.get(pk=obj.pk)
            if original.status == "pending" and obj.status in ("approved", "denied"):
                obj.reviewed_by = request.user
                obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(EarnedPremiumRecord)
class EarnedPremiumRecordAdmin(UnfoldModelAdmin):
    list_display = [
        "policy_link",
        "period_start",
        "period_end",
        "earned_amount",
        "unearned_amount",
        "calculation_date",
    ]
    list_filter = ["period_start", "period_end", "calculation_date"]
    search_fields = ["policy__policy_number", "policy__coverage_type"]
    ordering = ["-period_start"]
    readonly_fields = ["calculation_date", "created_at", "updated_at"]
    date_hierarchy = "period_start"

    fieldsets = (
        (
            "Policy",
            {
                "fields": ("policy",),
            },
        ),
        (
            "Reporting Period",
            {
                "fields": ("period_start", "period_end", "calculation_date"),
            },
        ),
        (
            "Premium Breakdown",
            {
                "fields": ("earned_amount", "unearned_amount"),
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

    @display(description="Policy")
    def policy_link(self, obj):
        url = reverse("admin:policies_policy_change", args=[obj.policy_id])
        return format_html('<a href="{}">{}</a>', url, obj.policy.policy_number)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "earned-premium-report/",
                self.admin_site.admin_view(self.earned_premium_report_view),
                name="policies_earned_premium_report",
            ),
        ]
        return custom_urls + urls

    def earned_premium_report_view(self, request):
        """Admin report page showing earned premium summary by month."""
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth

        rows = (
            EarnedPremiumRecord.objects.annotate(month=TruncMonth("period_start"))
            .values("month")
            .annotate(
                total_earned=Sum("earned_amount"),
                total_unearned=Sum("unearned_amount"),
            )
            .order_by("-month")
        )

        context = {
            **self.admin_site.each_context(request),
            "title": "Earned Premium Report",
            "rows": rows,
            "opts": self.model._meta,
        }
        return render(request, "admin/policies/earned_premium_report.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["report_url"] = reverse("admin:policies_earned_premium_report")
        return super().changelist_view(request, extra_context=extra_context)


# ── Finance Transactions View (3.1) ──────────────────────────────────────
#
# Finance admin tab: one row per product per PolicyTransaction, with
# filters, computed status, and CSV export. Registered in api/config/urls.py
# as `admin/reports/finance-transactions/`.


def _finance_compute_status(policy, today):
    """Compute status: Active / Payment Issue / Cancelled / Expired.

    Uses Policy.status plus current date vs. expiration_date.
    """
    if not policy:
        return "Active"
    status = (policy.status or "").lower()
    if status == "cancelled":
        return "Cancelled"
    if status in ("past_due",):
        return "Payment Issue"
    exp = policy.expiration_date
    if status == "expired" or (exp and exp < today):
        return "Expired"
    if status == "non_renewed":
        return "Expired" if exp and exp < today else "Active"
    return "Active"


FINANCE_STATUS_CHOICES = ["Active", "Payment Issue", "Cancelled", "Expired"]


def _finance_build_queryset(request):
    """Build the filtered PolicyTransaction queryset for the finance view."""
    from datetime import datetime as _dt

    qs = PolicyTransaction.objects.select_related("policy").order_by(
        "-accounting_date", "-created_at"
    )

    status_filter = (request.GET.get("status") or "").strip()
    date_from = (request.GET.get("collected_from") or "").strip()
    date_to = (request.GET.get("collected_to") or "").strip()
    is_brokered = (request.GET.get("is_brokered") or "").strip()

    if is_brokered == "yes":
        qs = qs.filter(policy__is_brokered=True)
    elif is_brokered == "no":
        qs = qs.filter(policy__is_brokered=False)

    def _parse(d):
        try:
            return _dt.strptime(d, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    df = _parse(date_from)
    dt_ = _parse(date_to)
    if df:
        qs = qs.filter(collected_date__gte=df)
    if dt_:
        qs = qs.filter(collected_date__lte=dt_)

    return qs, {
        "status": status_filter,
        "collected_from": date_from,
        "collected_to": date_to,
        "is_brokered": is_brokered,
    }


def _finance_rows(qs, status_filter):
    """Yield a dict per transaction with computed status applied."""
    today = timezone.localdate()
    for tx in qs.iterator():
        policy = tx.policy
        computed = _finance_compute_status(policy, today)
        if status_filter and computed != status_filter:
            continue
        # PolicyTransaction does not currently have a payout_id field; blank.
        payout_id = getattr(tx, "payout_id", "") or ""
        yield {
            "policy_number": policy.policy_number if policy else "",
            "coverage": policy.coverage_type if policy else "",
            "carrier": policy.carrier if policy else "",
            "is_brokered": bool(policy.is_brokered) if policy else False,
            "transaction_type": tx.get_transaction_type_display(),
            "effective_date": tx.effective_date,
            "accounting_date": tx.accounting_date,
            "collected_date": tx.collected_date,
            "gwp": tx.gross_written_premium,
            "admin_fee": tx.admin_fee_amount,
            "commission": tx.commission_amount,
            "payout_id": payout_id,
            "status": computed,
        }


def FinanceTransactionsView(request):
    """Finance tab: one row per product per PolicyTransaction.

    Shows policy_number, coverage, carrier, is_brokered, transaction_type,
    effective_date, accounting_date, gwp, admin_fee, commission, payout_id,
    and a computed status (Active / Payment Issue / Cancelled / Expired).

    Supports filters (status, collected_date from/to, is_brokered) and a
    CSV export via StreamingHttpResponse.

    Permission: restricted to finance/admin roles via
    ``is_corgi_full_access`` (full-access or admin group).
    """
    from django.core.exceptions import PermissionDenied
    from django.http import StreamingHttpResponse

    if not is_corgi_full_access(request.user):
        raise PermissionDenied("Finance tab requires finance/admin access.")

    qs, filters = _finance_build_queryset(request)
    status_filter = filters["status"]

    if request.GET.get("export") == "csv":

        class _Echo:
            def write(self, value):
                return value

        writer = csv.writer(_Echo())
        header = [
            "policy_number",
            "coverage",
            "carrier",
            "is_brokered",
            "transaction_type",
            "effective_date",
            "accounting_date",
            "collected_date",
            "gwp",
            "admin_fee",
            "commission",
            "payout_id",
            "status",
        ]

        def _stream():
            yield writer.writerow(header)
            for row in _finance_rows(qs, status_filter):
                yield writer.writerow(
                    [
                        row["policy_number"],
                        row["coverage"],
                        row["carrier"],
                        "yes" if row["is_brokered"] else "no",
                        row["transaction_type"],
                        row["effective_date"].isoformat()
                        if row["effective_date"]
                        else "",
                        row["accounting_date"].isoformat()
                        if row["accounting_date"]
                        else "",
                        row["collected_date"].isoformat()
                        if row["collected_date"]
                        else "",
                        row["gwp"] if row["gwp"] is not None else "",
                        row["admin_fee"] if row["admin_fee"] is not None else "",
                        row["commission"] if row["commission"] is not None else "",
                        row["payout_id"],
                        row["status"],
                    ]
                )

        filename = f"finance_transactions_{timezone.localdate().isoformat()}.csv"
        response = StreamingHttpResponse(_stream(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    # HTML render. Materialize rows (list) for template iteration + totals.
    rows = list(_finance_rows(qs, status_filter))
    totals = {
        "gwp": sum((r["gwp"] or Decimal("0")) for r in rows),
        "admin_fee": sum((r["admin_fee"] or Decimal("0")) for r in rows),
        "commission": sum((r["commission"] or Decimal("0")) for r in rows),
        "count": len(rows),
    }

    context = {
        **admin.site.each_context(request),
        "title": "Finance — Transactions by Product",
        "rows": rows,
        "totals": totals,
        "filters": filters,
        "status_choices": FINANCE_STATUS_CHOICES,
        "brokered_choices": [
            ("", "Any"),
            ("yes", "Brokered only"),
            ("no", "Non-brokered only"),
        ],
    }
    return render(request, "admin/policies/finance_transactions.html", context)
