"""
Policy-related Django models for the Corgi Insurance platform.

Core models:
- ``Policy``: Represents an active insurance policy bound to a quote.
- ``Payment``: Records individual payment events (Stripe-backed).
- ``PolicyTransaction``: Accounting record for new business, endorsements, cancellations.
- ``StateAllocation``: Premium allocation by US state for regulatory reporting.
- ``Cession``: Reinsurance cession record (non-brokered policies only).
"""

from django.db import models
from common.constants import TECHRRG_CARRIER
from common.models import StateChoices, TimestampedModel, SoftDeleteModel
from quotes.models import Quote
from policies.sequences import generate_policy_number


class Policy(SoftDeleteModel, TimestampedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("past_due", "Past Due"),
        ("pending_cancellation", "Pending Cancellation"),
        ("cancelled", "Cancelled"),
        ("expired", "Expired"),
        ("non_renewed", "Non-renewed"),
    ]

    BILLING_FREQUENCY_CHOICES = [
        ("annual", "Annual"),
        ("monthly", "Monthly"),
    ]

    policy_number = models.CharField(
        max_length=25,
        unique=True,
        verbose_name="Policy Number",
    )
    quote = models.ForeignKey(
        Quote,
        on_delete=models.PROTECT,
        related_name="policies",
        verbose_name="Quote",
    )
    coverage_type = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Coverage Type",
        help_text="The specific coverage type for this policy",
        blank=True,
        default="",
    )
    coi_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="COI Number",
        help_text="Certificate of Insurance number shared by policies from same purchase",
    )
    limits_retentions = models.JSONField(
        default=dict,
        verbose_name="Limits & Retentions (legacy)",
        help_text="Legacy JSON blob — use the dedicated fields below instead",
        blank=True,
    )
    per_occurrence_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Per Occurrence Limit",
        help_text="Maximum payout per single occurrence/claim",
    )
    aggregate_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Aggregate Limit",
        help_text="Maximum total payout for the policy period",
    )
    retention = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Retention / Deductible",
        help_text="Amount the insured pays before coverage kicks in",
    )
    premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Premium",
        help_text="Actual premium paid after all discounts applied",
    )
    effective_date = models.DateField(
        verbose_name="Effective Date",
    )
    expiration_date = models.DateField(
        db_index=True,
        verbose_name="Expiration Date",
    )
    purchased_at = models.DateTimeField(
        verbose_name="Purchased At",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Payment Intent ID",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
        verbose_name="Status",
    )
    billing_frequency = models.CharField(
        max_length=10,
        choices=BILLING_FREQUENCY_CHOICES,
        default="annual",
        verbose_name="Billing Frequency",
        help_text="Payment frequency (annual or monthly)",
    )
    monthly_premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monthly Premium",
        help_text="Monthly payment amount billed to the customer",
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Subscription ID",
        help_text="Stripe subscription ID for monthly billing",
    )
    stripe_customer_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Customer ID",
        help_text="Stripe customer ID for subscription management",
    )

    promo_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Promo Code",
        help_text="Promo code applied at purchase",
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Discount Percentage",
        help_text="Discount percentage applied (e.g., 20.00 for 20%)",
    )

    hubspot_deal_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="HubSpot Deal ID",
        help_text="ID of the corresponding HubSpot Deal for CRM sync",
    )
    is_brokered = models.BooleanField(
        default=False,
        verbose_name="Is Brokered",
        help_text="True if policy is brokered through external carrier",
    )
    force_ntic = models.BooleanField(
        default=False,
        verbose_name="Force NTIC Carrier",
        help_text="Override: force this policy to use NTIC carrier regardless of limit threshold. "
        "Use when NTIC is required below the $2M auto-trigger (e.g. manuscript endorsement).",
    )
    carrier = models.CharField(
        max_length=255,
        default=TECHRRG_CARRIER,
        db_index=True,
        verbose_name="Carrier",
        help_text="Insurance carrier name",
    )

    insured_legal_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Insured Legal Name",
        help_text="Legal name of the insured entity",
    )
    insured_fein = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Insured FEIN",
        help_text="Federal Employer Identification Number of the insured",
    )
    mailing_address = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Mailing Address",
        help_text="Insured mailing address {street, suite, city, state, zip}",
    )
    principal_state = models.CharField(
        max_length=2,
        choices=StateChoices.choices,
        null=True,
        blank=True,
        verbose_name="Principal State",
        help_text="Primary state of the insured",
    )
    paid_to_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Paid-to Date",
        help_text="Date through which premium has been paid",
    )

    # ── Claims-made policy fields ──────────────────────────────────────────────
    # All claims-made policies require retroactive coverage and reporting period
    # tracking for compliance purposes.

    retroactive_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Retroactive Date",
        help_text="Date from which prior acts are covered (claims-made basis). "
        "Typically set to the first inception date of continuous coverage.",
    )
    continuity_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Continuity Date",
        help_text="Date of continuous coverage with prior carrier. Used to determine "
        "whether retroactive date credit is available.",
    )
    prior_pending_litigation_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Prior & Pending Litigation Date",
        help_text="Cut-off date for prior and pending litigation exclusion. "
        "Claims or circumstances known before this date are excluded.",
    )
    extended_reporting_period_months = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Extended Reporting Period (months)",
        help_text="Duration of the tail coverage / ERP in months after policy expiration. "
        "Common values: 12, 24, 36, 60, 84 (unlimited = 999).",
    )

    RENEWAL_STATUS_CHOICES = [
        ("not_due", "Not Due"),
        ("offered", "Offered"),
        ("renewed", "Renewed"),
        ("non_renewed", "Non-Renewed"),
    ]

    renewal_status = models.CharField(
        max_length=20,
        choices=RENEWAL_STATUS_CHOICES,
        default="not_due",
        db_index=True,
        verbose_name="Renewal Status",
        help_text="Current renewal status of this policy",
    )
    auto_renew = models.BooleanField(
        default=False,
        verbose_name="Auto Renew",
        help_text="Whether this policy should be automatically renewed at expiration",
    )

    signed_agreement_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Signed Membership Agreement ID",
        help_text="Reference ID of the signed membership agreement document (e.g. DocuSign envelope ID). "
        "Required for Crime and Umbrella products. Populated by the membership agreement flow (H5).",
    )

    # Hash of the last HubSpot payload pushed to CRM. The outbound sync
    # task computes sha256 of the serialized payload and compares against
    # this value; identical payloads short-circuit without a network call.
    # This replaces the old threading.local() anti-loop guard with a
    # cross-process safe marker that also works across Celery workers.
    last_hubspot_sync_hash = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        verbose_name="Last HubSpot Sync Hash",
        help_text="sha256 of the last payload pushed to HubSpot. Used to "
        "detect inbound-webhook echoes and skip redundant pushes.",
    )

    # Stamped by the Stripe reconciler on every pass, regardless of whether
    # drift was detected. Lets the reconciler fairly round-robin through
    # all subscriptions instead of only scanning recently-updated rows.
    last_reconciled_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Last Reconciled At",
        help_text="Timestamp of the last Stripe reconciliation pass that "
        "inspected this policy (regardless of drift outcome).",
    )

    class Meta:
        db_table = "policies"
        verbose_name = "Policy"
        verbose_name_plural = "Policies"
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        errors = {}

        # effective_date must be before expiration_date
        if self.effective_date and self.expiration_date:
            # Cancelled / pending-cancellation policies get their
            # expiration pulled back to now or earlier; allow that shape.
            cancelled_states = ("cancelled", "pending_cancellation")
            if (
                self.effective_date >= self.expiration_date
                and self.status not in cancelled_states
            ):
                errors["expiration_date"] = (
                    "Expiration date must be after the effective date."
                )

        # premium must be >= 0
        if self.premium is not None and self.premium < 0:
            errors["premium"] = "Premium must be zero or positive."

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if not self.policy_number:
            state = self.quote.company.business_address.state
            self.policy_number = generate_policy_number(
                self.coverage_type, state, self.effective_date
            )
        # Run clean() validation on every save unless explicitly skipped
        if not kwargs.pop("skip_validation", False):
            self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Policy {self.policy_number}"


class Payment(TimestampedModel):
    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Policy",
    )
    stripe_invoice_id = models.CharField(
        max_length=255,
        verbose_name="Stripe Invoice ID",
        help_text="Real Stripe payment intent or invoice ID",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Amount",
    )
    status = models.CharField(
        max_length=20,
        verbose_name="Status",
    )
    paid_at = models.DateTimeField(
        verbose_name="Paid At",
    )
    payment_method = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Payment Method",
        help_text="Payment method used (card, ach, wire)",
    )
    refund_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Refund Amount",
        help_text="Amount refunded, if applicable",
    )
    refund_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name="Refund Reason",
        help_text="Reason for the refund",
    )
    refunded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Refunded At",
        help_text="Timestamp when the refund was processed",
    )

    class Meta:
        db_table = "payments"
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-paid_at"]

    def __str__(self):
        return f"Payment {self.stripe_invoice_id} - ${self.amount}"


class PolicyTransaction(TimestampedModel):
    TRANSACTION_TYPE_CHOICES = [
        ("new", "New Business"),
        ("renewal", "Renewal"),
        ("endorsement", "Endorsement"),
        ("cancel", "Cancellation"),
        ("reinstate", "Reinstatement"),
        ("audit", "Audit"),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPE_CHOICES,
    )
    effective_date = models.DateField()
    accounting_date = models.DateField()
    gross_written_premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )
    policy_fee_delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    membership_fee_delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    taxes_assessments_delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    total_billed_delta = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    collected_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    collected_date = models.DateField(
        null=True,
        blank=True,
    )
    collector_entity = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    admin_fee_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    admin_fee_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    admin_fee_recipient_entity = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )
    commission_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    description = models.TextField(
        null=True,
        blank=True,
        help_text="Human-readable description of what changed",
    )
    stripe_payout_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Stripe Payout ID",
        help_text="ID of the Stripe payout that settled the charge for this "
        "transaction. Populated from the charge.succeeded webhook or "
        "via the backfill_stripe_payouts management command. Used by "
        "finance to trace money from a policy to the bank deposit.",
    )

    class Meta:
        db_table = "policy_transactions"
        verbose_name = "Policy Transaction"
        verbose_name_plural = "Policy Transactions"
        ordering = ["-accounting_date", "-created_at"]

    def __str__(self):
        return f"{self.policy.policy_number} - {self.get_transaction_type_display()} - ${self.gross_written_premium}"


class StateAllocation(TimestampedModel):
    ALLOCATION_METHOD_CHOICES = [
        ("hq", "Headquarters"),
        ("payroll", "Payroll"),
        ("headcount", "Headcount"),
        ("revenue", "Revenue"),
        ("location_schedule", "Location Schedule"),
    ]

    transaction = models.ForeignKey(
        PolicyTransaction,
        on_delete=models.CASCADE,
        related_name="state_allocations",
    )
    state = models.CharField(
        max_length=2,
        choices=StateChoices.choices,
    )
    allocation_method = models.CharField(
        max_length=20,
        choices=ALLOCATION_METHOD_CHOICES,
        default="hq",
    )
    allocation_percent = models.DecimalField(
        max_digits=7,
        decimal_places=4,
    )
    allocated_premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
    )
    allocated_policy_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    allocated_membership_fee = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )
    allocated_taxes = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "state_allocations"
        verbose_name = "State Allocation"
        verbose_name_plural = "State Allocations"
        unique_together = ["transaction", "state"]
        ordering = ["state"]

    def __str__(self):
        return f"{self.transaction.policy.policy_number} - {self.state} - {self.allocation_percent}% - ${self.allocated_premium}"


class Cession(TimestampedModel):
    REINSURANCE_TYPE_CHOICES = [
        ("XOL", "Excess of Loss"),
        ("QS", "Quota Share"),
    ]

    transaction = models.ForeignKey(
        PolicyTransaction,
        on_delete=models.CASCADE,
        related_name="cessions",
    )
    treaty_id = models.CharField(
        max_length=50,
        verbose_name="Treaty ID",
    )
    reinsurance_type = models.CharField(
        max_length=3,
        choices=REINSURANCE_TYPE_CHOICES,
        verbose_name="Reinsurance Type",
    )
    attachment_point = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Attachment Point",
    )
    ceded_premium_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        verbose_name="Ceded Premium Rate",
    )
    ceded_premium_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Ceded Premium Amount",
    )
    reinsurer_name = models.CharField(
        max_length=100,
        verbose_name="Reinsurer Name",
    )

    class Meta:
        db_table = "cessions"
        verbose_name = "Cession"
        verbose_name_plural = "Cessions"
        unique_together = ["transaction", "treaty_id"]

    def __str__(self):
        return f"{self.transaction.policy.policy_number} - {self.treaty_id} - ${self.ceded_premium_amount}"


class PolicyRenewal(TimestampedModel):
    """Tracks renewal offers for expiring policies."""

    RENEWAL_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="renewals",
        verbose_name="Policy",
        help_text="The policy being renewed",
    )
    new_quote = models.ForeignKey(
        Quote,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="renewal_for",
        verbose_name="New Quote",
        help_text="The quote generated for the renewal offer",
    )
    status = models.CharField(
        max_length=10,
        choices=RENEWAL_STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the renewal offer",
    )
    offered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Offered At",
        help_text="When the renewal offer was sent to the customer",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Expires At",
        help_text="When the renewal offer expires",
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Accepted At",
        help_text="When the customer accepted the renewal",
    )
    notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Notes",
        help_text="Internal notes about this renewal",
    )

    class Meta:
        db_table = "policy_renewals"
        verbose_name = "Policy Renewal"
        verbose_name_plural = "Policy Renewals"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Renewal for {self.policy.policy_number} ({self.get_status_display()})"


class PolicyExcessLayer(TimestampedModel):
    """
    Tracks the RRG/Excess structure when Corgi brokers out to a primary carrier.

    When Corgi brokers a risk to a fronting or primary carrier, the Corgi RRG
    (Technology Risk Retention Group) retains an excess layer above the primary.
    Both carriers must appear on the COI and premium splits must be tracked
    for accounting and reporting purposes.

    Example:
        Primary: Travelers writes $1M xs $0 @ $8,000 premium
        Excess:  Corgi RRG writes $4M xs $1M @ $2,000 premium
        Total:   $5M aggregate, $10,000 total premium
    """

    policy = models.OneToOneField(
        Policy,
        on_delete=models.CASCADE,
        related_name="excess_layer",
        verbose_name="Policy",
        help_text="The brokered primary policy this excess layer sits above",
    )

    # Primary carrier details
    primary_carrier = models.CharField(
        max_length=255,
        verbose_name="Primary Carrier",
        help_text="Name of the primary/fronting carrier (e.g. Travelers, Markel)",
    )
    primary_carrier_naic = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Primary Carrier NAIC",
        help_text="NAIC code of the primary carrier",
    )
    primary_policy_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Primary Policy Number",
        help_text="Policy number issued by the primary carrier",
    )
    primary_limit = models.IntegerField(
        verbose_name="Primary Limit",
        help_text="Primary layer aggregate limit in dollars",
    )
    primary_retention = models.IntegerField(
        default=0,
        verbose_name="Primary Retention",
        help_text="Retention/deductible on the primary layer",
    )
    primary_premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Primary Premium",
        help_text="Premium paid to the primary carrier",
    )

    # Excess/RRG layer details
    excess_carrier = models.CharField(
        max_length=255,
        default="Technology Risk Retention Group, Inc.",
        verbose_name="Excess Carrier",
        help_text="Name of the excess carrier (default: Corgi RRG)",
    )
    excess_carrier_naic = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Excess Carrier NAIC",
        help_text="NAIC code of the excess carrier",
    )
    excess_attachment_point = models.IntegerField(
        verbose_name="Excess Attachment Point",
        help_text="Point at which the excess layer attaches (= primary_limit)",
    )
    excess_limit = models.IntegerField(
        verbose_name="Excess Limit",
        help_text="Excess layer limit in dollars (above attachment point)",
    )
    excess_premium = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Excess Premium",
        help_text="Premium retained by the excess carrier (Corgi RRG)",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Internal notes about this excess structure",
    )

    class Meta:
        db_table = "policy_excess_layers"
        verbose_name = "Policy Excess Layer"
        verbose_name_plural = "Policy Excess Layers"

    def __str__(self):
        return (
            f"{self.policy.policy_number} — {self.primary_carrier} primary "
            f"${self.primary_limit:,} xs $0 / {self.excess_carrier} xs ${self.excess_attachment_point:,}"
        )

    @property
    def total_premium(self):
        return self.primary_premium + self.excess_premium

    @property
    def total_limit(self):
        return self.primary_limit + self.excess_limit


class SurplusLinesFiling(TimestampedModel):
    """
    Tracks surplus lines filing requirements per policy.

    Every non-admitted policy requires:
    1. Diligent search documentation (proof admitted market was approached)
    2. State-specific surplus lines tax calculation
    3. Filing with the state surplus lines stamping office
    4. Deadline tracking (typically 15–60 days after binding)

    This model provides the compliance record for each filing.
    """

    FILING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("diligent_search_complete", "Diligent Search Complete"),
        ("filed", "Filed"),
        ("stamped", "Stamped"),
        ("overdue", "Overdue"),
        ("exempt", "Exempt"),
    ]

    policy = models.OneToOneField(
        Policy,
        on_delete=models.CASCADE,
        related_name="surplus_lines_filing",
        verbose_name="Policy",
        help_text="The non-admitted policy requiring surplus lines filing",
    )
    status = models.CharField(
        max_length=30,
        choices=FILING_STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Filing Status",
    )

    # State info
    filing_state = models.CharField(
        max_length=2,
        verbose_name="Filing State",
        help_text="State in which this surplus lines policy must be filed",
    )
    stamping_office = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stamping Office",
        help_text="Name of the state surplus lines stamping office (e.g. SLSOC for CA)",
    )

    # Tax
    surplus_lines_tax_rate = models.DecimalField(
        max_digits=6,
        decimal_places=4,
        verbose_name="Surplus Lines Tax Rate",
        help_text="State surplus lines tax rate as a decimal (e.g. 0.0350 for 3.5%)",
    )
    surplus_lines_tax_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Surplus Lines Tax Amount",
        help_text="Calculated tax amount in dollars",
    )
    stamping_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Stamping Fee",
        help_text="Stamping office fee in dollars (varies by state)",
    )

    # Diligent search
    diligent_search_completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Diligent Search Completed At",
        help_text="When the diligent search of the admitted market was documented",
    )
    admitted_carriers_approached = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Admitted Carriers Approached",
        help_text="List of admitted carriers approached with declination reasons",
    )
    diligent_search_document_key = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="Diligent Search Document S3 Key",
        help_text="S3 key for the diligent search affidavit/documentation",
    )

    # Filing deadlines and timestamps
    binding_date = models.DateField(
        verbose_name="Binding Date",
        help_text="Date the policy was bound (start of filing deadline clock)",
    )
    filing_deadline = models.DateField(
        verbose_name="Filing Deadline",
        help_text="Deadline for filing with the stamping office",
    )
    filed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Filed At",
        help_text="When the filing was actually submitted",
    )
    stamped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Stamped At",
        help_text="When the stamping office confirmed the filing",
    )
    stamping_reference = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Stamping Reference",
        help_text="Reference number issued by the stamping office",
    )

    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Notes",
        help_text="Internal compliance notes",
    )

    class Meta:
        db_table = "surplus_lines_filings"
        verbose_name = "Surplus Lines Filing"
        verbose_name_plural = "Surplus Lines Filings"
        ordering = ["filing_deadline"]
        indexes = [
            models.Index(fields=["status", "filing_deadline"]),
            models.Index(fields=["filing_state", "status"]),
        ]

    def __str__(self):
        return f"SL Filing — {self.policy.policy_number} ({self.filing_state}) — {self.get_status_display()}"

    @property
    def is_overdue(self):
        from django.utils import timezone

        return (
            self.status not in ("filed", "stamped", "exempt")
            and self.filing_deadline < timezone.now().date()
        )


class CoverageModificationRequest(TimestampedModel):
    """
    Tracks customer requests to modify coverage on an existing policy.

    Customers submit a modification request via the portal. Underwriters
    review and approve/deny the change through Django admin.

    Examples:
        - Increase aggregate limit from 1M to 2M
        - Add an additional insured endorsement
        - Reduce retention from 25K to 10K
    """

    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("approved", "Approved"),
        ("denied", "Denied"),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="modification_requests",
        verbose_name="Policy",
        help_text="The policy to be modified",
    )
    requested_changes = models.JSONField(
        verbose_name="Requested Changes",
        help_text="JSON dict describing the requested changes (e.g. new limits, added endorsements)",
    )
    reason = models.TextField(
        verbose_name="Reason",
        help_text="Customer-provided reason for the modification request",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Status",
    )
    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coverage_modification_requests",
        verbose_name="Requested By",
        help_text="User who submitted the modification request",
    )
    reviewed_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_modification_requests",
        verbose_name="Reviewed By",
        help_text="Staff user who approved or denied the request",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Reviewed At",
        help_text="When the request was approved or denied",
    )
    reviewer_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name="Reviewer Notes",
        help_text="Internal notes from the underwriter",
    )

    class Meta:
        db_table = "coverage_modification_requests"
        verbose_name = "Coverage Modification Request"
        verbose_name_plural = "Coverage Modification Requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ModRequest #{self.pk} - {self.policy.policy_number} ({self.get_status_display()})"


class ReviewSchedule(TimestampedModel):
    """Annual coverage review scheduled by a policyholder with their AE."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("confirmed", "Confirmed"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="review_schedules",
        verbose_name="Organization",
    )
    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review_schedules",
        verbose_name="Requested By",
    )
    preferred_date = models.DateField(
        verbose_name="Preferred Date",
        help_text="Customer's preferred date for the review call",
    )
    preferred_time = models.CharField(
        max_length=10,
        verbose_name="Preferred Time",
        help_text="Preferred time in HH:MM format (e.g. 14:00)",
        blank=True,
        default="",
    )
    timezone = models.CharField(
        max_length=50,
        default="America/New_York",
        verbose_name="Timezone",
    )
    topics = models.TextField(
        blank=True,
        default="",
        verbose_name="Topics to Discuss",
        help_text="Comma-separated topics the customer wants to discuss",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Additional Notes",
        help_text="Any extra context from the customer",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Status",
    )
    confirmed_datetime = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Confirmed Datetime",
        help_text="Final confirmed date/time set by the AE",
    )
    ae_notes = models.TextField(
        blank=True,
        default="",
        verbose_name="AE Notes",
        help_text="Internal notes from the Account Executive",
    )

    class Meta:
        db_table = "review_schedules"
        verbose_name = "Review Schedule"
        verbose_name_plural = "Review Schedules"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Review for {self.organization.name} on {self.preferred_date} ({self.get_status_display()})"


class RevenueSplit(TimestampedModel):
    """
    Persisted output of the revenue-recognition flow chart.

    One row per ``PolicyTransaction`` run through
    ``stripe_integration.revenue_service.revenue_split``. The amounts
    stored here are what the ``daily_revenue_split_export`` task emits
    to S3 (``corgi-finance/daily-splits/YYYY-MM-DD.csv``) and what will
    eventually drive the Mercury/Meow wire transfers.

    Buckets:
        - ``corgi_admin``: Corgi Admin cut (22% non-brokered / 100% brokered)
        - ``techrrg``:     TechRRG cut (46.7% + collected tax, non-brokered)
        - ``corgire``:     CorgiRe reinsurance cut (28.3%, non-brokered)
        - ``dane``:        Dane override (3%, non-brokered)
        - ``admin_fee``:   Policy / admin fees that bypass the premium split
    """

    transaction = models.ForeignKey(
        PolicyTransaction,
        on_delete=models.CASCADE,
        related_name="revenue_splits",
        verbose_name="Policy Transaction",
        help_text="Transaction this revenue split was computed from.",
    )
    corgi_admin = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Corgi Admin",
        help_text="Dollars allocated to the Corgi Admin bucket.",
    )
    techrrg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="TechRRG",
        help_text="Dollars allocated to TechRRG (includes collected tax on non-brokered policies).",
    )
    corgire = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="CorgiRe",
        help_text="Dollars allocated to the CorgiRe reinsurance bucket.",
    )
    dane = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Dane",
        help_text="Dollars allocated to the Dane override bucket.",
    )
    admin_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Admin Fee",
        help_text="Policy / admin fees routed outside the premium split.",
    )
    computed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Computed At",
        help_text="When the split was computed.",
    )

    class Meta:
        db_table = "revenue_splits"
        verbose_name = "Revenue Split"
        verbose_name_plural = "Revenue Splits"
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["transaction", "computed_at"]),
        ]

    def __str__(self):
        return (
            f"RevenueSplit #{self.pk} — tx={self.transaction_id} "
            f"(admin=${self.corgi_admin}, techrrg=${self.techrrg}, "
            f"corgire=${self.corgire}, dane=${self.dane}, fee=${self.admin_fee})"
        )


class EarnedPremiumRecord(TimestampedModel):
    """
    GAAP revenue recognition record.
    Insurance premiums are earned over the policy period, not at purchase.
    This model tracks earned vs unearned premium per policy per reporting period.
    """

    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="earned_premium_records",
        verbose_name="Policy",
    )
    period_start = models.DateField(
        verbose_name="Period Start",
        help_text="Start of the reporting period (usually first day of month)",
    )
    period_end = models.DateField(
        verbose_name="Period End",
        help_text="End of the reporting period (usually last day of month)",
    )
    earned_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Earned Premium",
        help_text="Premium earned during this period (prorated portion of total premium)",
    )
    unearned_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Unearned Premium",
        help_text="Premium not yet earned (remaining unearned balance at period end)",
    )
    calculation_date = models.DateField(
        auto_now_add=True,
        verbose_name="Calculation Date",
        help_text="Date this record was calculated",
    )

    class Meta:
        db_table = "earned_premium_records"
        verbose_name = "Earned Premium Record"
        verbose_name_plural = "Earned Premium Records"
        ordering = ["-period_start"]
        unique_together = ["policy", "period_start", "period_end"]

    def __str__(self):
        return f"{self.policy.policy_number}: ${self.earned_amount} earned ({self.period_start} – {self.period_end})"


class EntityExpense(TimestampedModel):
    """
    Per-entity expense record used by the ROI / burn / runway dashboard.

    Each row represents a cash outflow attributable to one of the legal
    entities the revenue-split flow chart recognises:

        corgi_admin, techrrg, corgire, dane

    Expenses drive two calculations in ``analytics.entity_finance``:
        * ROI     = (revenue − expenses) / expenses  per entity & window
        * Burn    = sum of expenses − revenue over the trailing 30 days
        * Runway  = cash_balance / monthly_burn (in months)
    """

    ENTITY_CHOICES = [
        ("corgi_admin", "Corgi Admin"),
        ("techrrg", "TechRRG"),
        ("corgire", "CorgiRe"),
        ("dane", "Dane"),
    ]

    entity = models.CharField(
        max_length=20,
        choices=ENTITY_CHOICES,
        db_index=True,
        verbose_name="Entity",
        help_text="Legal entity this expense is booked against.",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Amount",
        help_text="Dollars spent (cash outflow).",
    )
    category = models.CharField(
        max_length=50,
        db_index=True,
        verbose_name="Category",
        help_text="Expense category (e.g. payroll, vendor, insurance, software).",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Human-readable description of the expense.",
    )
    incurred_at = models.DateField(
        db_index=True,
        verbose_name="Incurred At",
        help_text="Date the expense was incurred.",
    )

    class Meta:
        db_table = "entity_expenses"
        verbose_name = "Entity Expense"
        verbose_name_plural = "Entity Expenses"
        ordering = ["-incurred_at"]
        indexes = [
            models.Index(fields=["entity", "incurred_at"]),
        ]

    def __str__(self):
        return f"{self.entity} — ${self.amount} ({self.category}, {self.incurred_at})"
