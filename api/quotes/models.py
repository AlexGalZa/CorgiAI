"""
Quote-related Django models for the Corgi Insurance platform.

Core models:
- ``Address``: Business address with US state validation.
- ``Company``: Organization details including financials and structure.
- ``ReferralPartner``: Partners who refer customers for commission.
- ``Quote``: Central model tracking the quote lifecycle from draft to purchase.
- ``QuoteDocument``: Files uploaded during the quoting process.
- ``UnderwriterOverride``: Manual override for bypassing rating validation.
- ``CustomProduct``: Brokered coverage priced by an underwriter.
- ``CoverageType``: Normalized coverage type definitions.
- ``PromoCode``: Promotional codes for discounts.
"""

from django.conf import settings
from django.db import models
from common.models import TimestampedModel, SoftDeleteModel, BaseDocument, StateChoices
from common.encrypted_fields import EncryptedCharField
from common.utils import generate_short_id


class Address(TimestampedModel):
    street_address = models.CharField(
        max_length=255,
        verbose_name="Street Address",
        help_text="Street address line",
    )
    suite = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Suite/Unit",
        help_text="Suite, unit, or apartment number",
    )
    city = models.CharField(
        max_length=100,
        verbose_name="City",
        help_text="City name",
    )
    state = models.CharField(
        max_length=2,
        choices=StateChoices.choices,
        verbose_name="State",
        help_text="US state or territory",
    )
    zip = models.CharField(
        max_length=10,
        verbose_name="ZIP Code",
        help_text="ZIP or postal code",
    )
    country = models.CharField(
        max_length=2,
        default="US",
        verbose_name="Country",
        help_text="Country code (default: US)",
    )

    class Meta:
        db_table = "addresses"
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        parts = [self.street_address, self.city, self.state, self.zip]
        return ", ".join(parts)


class Company(TimestampedModel):
    ORGANIZATION_TYPES = [
        ("individual", "Individual"),
        ("partnership", "Partnership"),
        ("corporation", "Corporation"),
        ("llc", "LLC"),
        ("other", "Other"),
    ]

    PROFIT_TYPES = [
        ("for-profit", "For Profit"),
        ("not-for-profit", "Not For Profit"),
    ]

    business_address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        related_name="company",
        verbose_name="Business Address",
        help_text="Business address",
    )

    # Organization Info
    entity_legal_name = models.CharField(
        max_length=255,
        verbose_name="Entity Legal Name",
        help_text="Legal name of the organization",
        default="",
    )
    dba_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="DBA / Trade Name",
        help_text="Doing Business As (trade name), if different from legal name",
    )
    naics_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name="NAICS Code",
        help_text="North American Industry Classification System code",
    )
    naics_description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="NAICS Description",
        help_text="Auto-filled description from NAICS code lookup",
    )
    type = models.CharField(
        max_length=20,
        choices=ORGANIZATION_TYPES,
        verbose_name="Organization Type",
        help_text="Legal structure of the organization",
    )
    type_other = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Other Organization Type",
        help_text="Specify organization type if 'Other' is selected",
    )
    profit_type = models.CharField(
        max_length=20,
        choices=PROFIT_TYPES,
        verbose_name="Profit Type",
        help_text="Whether the organization is for-profit or not-for-profit",
    )
    federal_ein = EncryptedCharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Federal EIN",
        help_text="Federal Employer Identification Number — encrypted at rest",
    )
    # PII bank details — encrypted at rest (V3 #52)
    bank_account_number = EncryptedCharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Bank Account Number",
        help_text="ACH bank account number — encrypted at rest",
    )
    bank_routing_number = EncryptedCharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Bank Routing Number",
        help_text="ACH routing number — encrypted at rest",
    )
    business_start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Business Start Date",
        help_text="Date the business started",
    )
    estimated_payroll = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Estimated Payroll",
        help_text="Estimated annual payroll",
    )

    # Financial Details
    last_12_months_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Last 12 Months Revenue",
        help_text="Total revenue for the last 12 months",
    )
    projected_next_12_months_revenue = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Projected Next 12 Months Revenue",
        help_text="Projected revenue for the next 12 months",
    )
    full_time_employees = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Full Time Employees",
        help_text="Number of full time employees",
    )
    part_time_employees = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Part Time Employees",
        help_text="Number of part time employees",
    )

    # Structure/Operations
    is_technology_company = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Is Technology Company",
        help_text="Whether the company develops, uses, or relies on technology as a core part of its operations",
    )
    has_subsidiaries = models.BooleanField(
        default=False,
        verbose_name="Has Subsidiaries",
        help_text="Whether the company has subsidiaries",
    )
    all_entities_covered = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="All Entities Covered",
        help_text="Whether all subsidiary entities are covered",
    )
    subsidiaries_explanation = models.TextField(
        null=True,
        blank=True,
        verbose_name="Subsidiaries Explanation",
        help_text="Details about subsidiary entities and coverage",
    )
    planned_acquisitions = models.BooleanField(
        default=False,
        verbose_name="Planned Acquisitions",
        help_text="Whether the company has planned acquisitions",
    )
    planned_acquisitions_details = models.TextField(
        null=True,
        blank=True,
        verbose_name="Planned Acquisitions Details",
        help_text="Details about planned acquisitions",
    )
    business_description = models.TextField(
        verbose_name="Business Description",
        help_text="Description of the company's business operations",
    )

    class Meta:
        db_table = "companies"
        verbose_name_plural = "Companies"

    def __str__(self):
        if self.entity_legal_name:
            return self.entity_legal_name
        return f"Company {self.id} - {self.business_address.city}, {self.business_address.state}"


class ReferralPartner(TimestampedModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Display name of the referral partner",
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="Slug",
        help_text="Unique identifier used in referral URLs (e.g. 'remax')",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="Commission Rate (%)",
        help_text="Commission percentage owed to this partner on billing premium",
    )
    notification_emails = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Notification Emails",
        help_text="List of email addresses to notify on account creation and quote submission for this partner's referrals",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
    )

    class Meta:
        db_table = "referral_partners"
        verbose_name = "Referral Partner"
        verbose_name_plural = "Referral Partners"

    def __str__(self):
        return f"{self.name} ({self.slug})"


class Quote(SoftDeleteModel, TimestampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("needs_review", "Needs Review"),
        ("quoted", "Quoted"),
        ("purchased", "Purchased"),
        ("declined", "Declined"),
    ]

    BILLING_FREQUENCY_CHOICES = [
        ("annual", "Annual"),
        ("monthly", "Monthly"),
    ]

    COVERAGE_CHOICES = [
        ("commercial-general-liability", "Commercial General Liability"),
        ("media-liability", "Media Liability"),
        ("directors-and-officers", "Directors & Officers"),
        ("representations-warranties", "Representations & Warranties"),
        ("technology-errors-and-omissions", "Technology E&O"),
        ("cyber-liability", "Cyber Liability"),
        ("fiduciary-liability", "Fiduciary Liability"),
        ("hired-and-non-owned-auto", "Hired & Non-Owned Auto"),
        ("employment-practices-liability", "Employment Practices Liability"),
        ("custom-commercial-auto", "Commercial Auto"),
        ("custom-crime", "Crime Insurance"),
        ("custom-kidnap-ransom", "Kidnap & Ransom"),
        ("custom-med-malpractice", "Medical Malpractice"),
        ("custom-workers-comp", "Workers Compensation"),
        ("custom-bop", "Business Owners Policy"),
        ("custom-umbrella", "Umbrella"),
        ("custom-excess-liability", "Excess Liability"),
    ]

    COMPANY_REVIEW_CHOICES = [
        ("claims_history", "Claims History Review"),
        ("company", "Company Eligibility Review"),
    ]

    quote_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        editable=False,
        verbose_name="Quote Number",
        help_text="Unique quote identifier (auto-generated)",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="quotes",
        verbose_name="Company",
        help_text="Company requesting the quote",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quotes",
        verbose_name="User",
        help_text="User who submitted the quote",
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="quotes",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted",
        verbose_name="Status",
        help_text="Current status of the quote",
    )
    coverages = models.JSONField(
        default=list,
        verbose_name="Coverages",
        help_text="List of currently selected coverage types",
    )
    available_coverages = models.JSONField(
        default=list,
        verbose_name="Available Coverages",
        help_text="List of all coverages user can toggle (preserves original selections)",
    )
    coverage_data = models.JSONField(
        default=dict,
        verbose_name="Coverage Data",
        help_text="Coverage-specific questionnaire data",
    )
    limits_retentions = models.JSONField(
        default=dict,
        verbose_name="Limits & Retentions",
        help_text="Requested limits and retention amounts per coverage",
    )
    claims_history = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name="Claims History",
        help_text="Loss history and insurance history",
    )
    quote_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Base Annual Premium",
        help_text="Raw annual premium before promo code discounts. Includes 10% annual discount. Does not include brokered coverages.",
    )
    quoted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Quoted At",
        help_text="Timestamp when quote was provided",
    )
    form_data_snapshot = models.JSONField(
        default=dict,
        verbose_name="Form Data Snapshot",
        help_text="Complete snapshot of submitted form data",
    )
    rating_result = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name="Rating Result",
        help_text="Premium calculation result including breakdown per coverage and review reasons",
    )
    initial_ai_classifications = models.JSONField(
        default=dict,
        null=True,
        blank=True,
        verbose_name="Initial AI Classifications",
        help_text="First AI classification results per coverage (preserved across recalculations)",
    )
    billing_frequency = models.CharField(
        max_length=10,
        choices=BILLING_FREQUENCY_CHOICES,
        default="annual",
        verbose_name="Billing Frequency",
        help_text="Payment frequency selected by the customer (annual or monthly)",
    )
    promo_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Promo Code",
        help_text="Promotional code from landing page to be auto-applied at checkout",
    )
    completed_steps = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Completed Steps",
        help_text="List of step IDs that have been completed",
    )
    current_step = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Current Step",
        help_text="The current step ID where the user left off",
    )
    parent_quote = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_quotes",
        verbose_name="Parent Quote",
        help_text="For split quotes: links to the original quote this was split from",
    )
    referral_partner = models.ForeignKey(
        ReferralPartner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes",
        verbose_name="Referral Partner",
        help_text="Partner who referred this quote via referral link",
    )
    lead_source = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ("organic", "Organic"),
            ("referral", "Referral"),
            ("outbound", "Outbound"),
            ("partner", "Partner"),
            ("paid", "Paid Ad"),
            ("other", "Other"),
        ],
        verbose_name="Lead Source",
        help_text="How this lead was acquired",
    )
    assigned_ae = models.ForeignKey(
        "users.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_quotes",
        verbose_name="Assigned AE",
        help_text="Account executive assigned to this quote",
    )
    utm_source = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="UTM Source",
        help_text="Traffic source captured from the utm_source query param (e.g. 'google', 'linkedin')",
    )
    utm_medium = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="UTM Medium",
        help_text="Traffic medium captured from the utm_medium query param (e.g. 'cpc', 'email')",
    )
    utm_campaign = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        verbose_name="UTM Campaign",
        help_text="Campaign identifier captured from the utm_campaign query param",
    )
    referrer_url = models.TextField(
        blank=True,
        default="",
        verbose_name="Referrer URL",
        help_text="document.referrer value at the time the quote was created",
    )
    landing_page_url = models.TextField(
        blank=True,
        default="",
        verbose_name="Landing Page URL",
        help_text="Initial landing page URL (including query string) where the visitor was acquired",
    )

    class Meta:
        db_table = "quotes"
        verbose_name = "Quote"
        verbose_name_plural = "Quotes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["quote_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    # Valid status transitions (from_status → set of allowed to_statuses)
    VALID_STATUS_TRANSITIONS = {
        "draft": {"submitted", "declined"},
        "submitted": {"needs_review", "quoted", "declined"},
        "needs_review": {"quoted", "declined"},
        # 'draft' is allowed so QuoteService.save_step can revert a
        # quoted quote when the user edits a step and the rating has to
        # be recomputed.
        "quoted": {"purchased", "declined", "draft"},
        "purchased": set(),  # terminal state
        "declined": {"draft"},  # allow re-opening a declined quote
    }

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        # quote_amount must be >= 0 if set
        if self.quote_amount is not None and self.quote_amount < 0:
            errors["quote_amount"] = "Quote amount must be zero or positive."

        # Validate status transitions (only when updating an existing record)
        if self.pk:
            try:
                old = Quote.objects.only("status").get(pk=self.pk)
            except Quote.DoesNotExist:
                old = None
            if old and old.status != self.status:
                allowed = self.VALID_STATUS_TRANSITIONS.get(old.status, set())
                if self.status not in allowed:
                    errors["status"] = (
                        f"Invalid status transition: '{old.status}' → '{self.status}'. "
                        f"Allowed: {', '.join(sorted(allowed)) or 'none (terminal state)'}."
                    )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.quote_number:
            self.quote_number = generate_short_id()
        # Run clean() validation on every save unless explicitly skipped
        if not kwargs.pop("skip_validation", False):
            self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quote_number}"


class QuoteDocument(BaseDocument):
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="documents",
    )

    class Meta:
        db_table = "quote_documents"

    def __str__(self):
        return f"{self.original_filename} - {self.quote.quote_number}"


class UnderwriterOverride(TimestampedModel):
    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="underwriter_overrides",
        verbose_name="Quote",
    )
    coverage = models.CharField(
        max_length=50,
        choices=Quote.COVERAGE_CHOICES + Quote.COMPANY_REVIEW_CHOICES,
        verbose_name="Coverage",
    )
    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        verbose_name="Premium Multiplier",
        help_text="Multiplier applied to the calculated premium (1.0 = no change, 1.5 = 50% increase, 0.8 = 20% discount)",
    )
    bypass_validation = models.BooleanField(
        default=True,
        verbose_name="Bypass Validation",
        help_text="If true, skip validation errors for this coverage and use the multiplier on base premium",
    )
    comment = models.TextField(
        verbose_name="Underwriter Comment",
        help_text="Explanation for the override decision",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="underwriter_overrides",
        verbose_name="Created By",
    )

    class Meta:
        db_table = "underwriter_overrides"
        verbose_name = "Underwriter Override"
        verbose_name_plural = "Underwriter Overrides"
        unique_together = ["quote", "coverage"]

    def __str__(self):
        return f"{self.quote.quote_number} - {self.get_coverage_display()} (x{self.multiplier})"


class CustomProduct(TimestampedModel):
    PRODUCT_TYPES = [
        ("custom-cgl", "Commercial General Liability (CGL)"),
        ("custom-do", "Directors & Officers (D&O)"),
        ("custom-eo", "Errors & Omissions (E&O)"),
        ("custom-tech-eo", "Technology E&O"),
        ("custom-cyber", "Cyber Liability"),
        ("custom-epli", "Employment Practices Liability (EPLI)"),
        ("custom-workers-comp", "Workers Compensation"),
        ("custom-bop", "Business Owners Policy"),
        ("custom-umbrella", "Umbrella"),
        ("custom-excess-liability", "Excess Liability"),
        ("custom-hnoa", "Hired & Non-Owned Auto (HNOA)"),
        ("custom-crime", "Crime Insurance"),
        ("custom-kidnap-ransom", "Kidnap & Ransom"),
        ("custom-med-malpractice", "Medical Malpractice"),
        ("custom-property", "Commercial Property"),
        ("custom-surety", "Surety Bond"),
        ("custom-fiduciary", "Fiduciary Liability"),
        ("custom-media", "Media Liability"),
        ("custom-commercial-auto", "Commercial Auto"),
        ("custom-other", "Other"),
    ]

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        related_name="custom_products",
        verbose_name="Quote",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Product Name",
        help_text="Display name for this custom product",
    )
    product_type = models.CharField(
        max_length=50,
        choices=PRODUCT_TYPES,
        verbose_name="Product Type",
    )
    per_occurrence_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Per Occurrence Limit",
    )
    aggregate_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Aggregate Limit",
    )
    retention = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Retention",
    )
    price = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Price",
        help_text="Annual premium for this custom product",
    )
    carrier = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Carrier",
        help_text="Insurance carrier for this custom product",
    )
    fulfills_coverage = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Fulfills Brokered Coverage",
        help_text="If set, this product fulfills the selected brokered coverage and auto-creates an underwriter override",
    )

    original_filename = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, null=True, blank=True)
    s3_key = models.CharField(max_length=500, null=True, blank=True)
    s3_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        db_table = "custom_products"
        verbose_name = "Brokered Coverage"
        verbose_name_plural = "Brokered Coverages"

    def __str__(self):
        return f"{self.name} - {self.quote.quote_number}"


class CoverageType(TimestampedModel):
    """Normalized coverage type definitions.

    Replaces scattered coverage type constants across Quote.COVERAGE_CHOICES,
    CustomProduct.PRODUCT_TYPES, and various constants files.
    """

    TIER_CHOICES = [
        ("instant", "Instant (RRG-rated, bound online)"),
        ("brokered_form", "Brokered with Form (extra questionnaire)"),
        ("brokered_intent", "Brokered Intent-Only (no extra form)"),
    ]

    slug = models.SlugField(
        max_length=60,
        unique=True,
        verbose_name="Slug",
        help_text="Unique identifier slug (e.g. 'cyber-liability', 'custom-workers-comp')",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Human-readable display name",
    )
    tier = models.CharField(
        max_length=20,
        choices=TIER_CHOICES,
        db_index=True,
        verbose_name="Tier",
        help_text="Coverage tier: instant (rated by Corgi engine), brokered_form, or brokered_intent",
    )
    carrier_default = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Default Carrier",
        help_text="Default insurance carrier for this coverage type",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether this coverage type is currently available for selection",
    )
    description = models.TextField(
        null=True,
        blank=True,
        verbose_name="Description",
        help_text="Optional description of this coverage type",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        verbose_name="Display Order",
        help_text="Order in which to display this coverage type in the UI",
    )

    class Meta:
        db_table = "coverage_types"
        verbose_name = "Coverage Type"
        verbose_name_plural = "Coverage Types"
        ordering = ["display_order", "name"]

    def __str__(self):
        return f"{self.name} ({self.slug})"


class PromoCode(TimestampedModel):
    """Promotional codes for discounts. Replaces string-only promo code validation against Stripe."""

    DISCOUNT_TYPE_CHOICES = [
        ("percentage", "Percentage"),
        ("fixed", "Fixed Amount"),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name="Code",
        help_text="Promotional code string (case-insensitive)",
    )
    stripe_coupon_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Stripe Coupon ID",
        help_text="Associated Stripe coupon ID for payment processing",
    )
    discount_type = models.CharField(
        max_length=10,
        choices=DISCOUNT_TYPE_CHOICES,
        verbose_name="Discount Type",
        help_text="Type of discount: percentage or fixed amount",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Discount Value",
        help_text="Discount amount (percentage value like 20.00 for 20%, or fixed dollar amount)",
    )
    valid_from = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Valid From",
        help_text="Start of the promotional period (null = immediately valid)",
    )
    valid_until = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Valid Until",
        help_text="End of the promotional period (null = no expiration)",
    )
    max_uses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Max Uses",
        help_text="Maximum number of times this code can be redeemed (null = unlimited)",
    )
    use_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Use Count",
        help_text="Number of times this code has been redeemed",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether this promo code is currently usable",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_promo_codes",
        verbose_name="Created By",
        help_text="Admin who created this promo code",
    )

    class Meta:
        db_table = "promo_codes"
        verbose_name = "Promo Code"
        verbose_name_plural = "Promo Codes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.code} ({self.discount_value}{'%' if self.discount_type == 'percentage' else '$'})"

    @property
    def is_valid(self):
        from django.utils import timezone

        if not self.is_active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_uses is not None and self.use_count >= self.max_uses:
            return False
        return True
