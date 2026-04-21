"""
Stripe-related models for the Corgi Insurance platform.

Models:
- RefundRequest: Tracks customer refund requests with approval workflow.
- DunningRecord: Tracks failed payment dunning state per policy.
"""

from django.db import models
from django.utils import timezone
from common.models import TimestampedModel
from policies.models import Policy


class RefundRequest(TimestampedModel):
    """
    Tracks refund requests with an approval workflow.

    Flow: pending → approved/denied → processed

    On approval, the admin triggers a Stripe refund for the specified amount.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("denied", "Denied"),
        ("processed", "Processed"),
        ("failed", "Failed"),
    ]

    REASON_CHOICES = [
        ("cancellation", "Policy Cancellation"),
        ("duplicate_charge", "Duplicate Charge"),
        ("billing_error", "Billing Error"),
        ("coverage_not_needed", "Coverage No Longer Needed"),
        ("underwriting_rejection", "Underwriting Rejection"),
        ("customer_dissatisfaction", "Customer Dissatisfaction"),
        ("other", "Other"),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="refund_requests",
        verbose_name="Policy",
        help_text="The policy this refund is related to.",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Refund Amount",
        help_text="Amount to refund in USD.",
    )
    reason = models.CharField(
        max_length=30,
        choices=REASON_CHOICES,
        default="other",
        verbose_name="Reason",
        help_text="Reason category for the refund request.",
    )
    reason_detail = models.TextField(
        blank=True,
        default="",
        verbose_name="Reason Detail",
        help_text="Additional details about the refund reason.",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True,
        verbose_name="Status",
    )
    requested_by = models.ForeignKey(
        "users.User",
        on_delete=models.PROTECT,
        related_name="requested_refunds",
        verbose_name="Requested By",
        help_text="User who submitted the refund request.",
    )
    approved_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_refunds",
        verbose_name="Approved/Denied By",
        help_text="Staff user who approved or denied this request.",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Approved/Denied At",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Processed At",
        help_text="When the Stripe refund was successfully processed.",
    )
    denial_reason = models.TextField(
        blank=True,
        default="",
        verbose_name="Denial Reason",
        help_text="Explanation shown to the customer when denied.",
    )

    # Stripe tracking
    stripe_refund_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Refund ID",
        help_text="Stripe refund object ID (re_...) after processing.",
    )
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Payment Intent ID",
        help_text="The Stripe PaymentIntent being refunded.",
    )

    class Meta:
        db_table = "refund_requests"
        verbose_name = "Refund Request"
        verbose_name_plural = "Refund Requests"
        ordering = ["-created_at"]

    def __str__(self):
        return f"RefundRequest #{self.pk} — {self.policy.policy_number} ${self.amount} ({self.status})"


class DunningRecord(TimestampedModel):
    """
    Tracks the dunning state for a policy with a failed payment.

    Dunning schedule:
    - Day 0: payment fails → create DunningRecord (attempt_count=1)
    - Day 1: retry → attempt_count=2
    - Day 3: retry → attempt_count=3
    - Day 7: final retry → if still fails, auto-cancel policy

    Status: active → resolved (payment recovered) | cancelled (policy cancelled)
    """

    STATUS_CHOICES = [
        ("active", "Active — awaiting retry"),
        ("resolved", "Resolved — payment recovered"),
        ("cancelled", "Cancelled — policy cancelled after max retries"),
    ]

    RETRY_DAYS = [1, 3, 7]  # Days after initial failure to retry

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="dunning_records",
        verbose_name="Policy",
        help_text="The policy with a failed payment.",
    )
    attempt_count = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Attempt Count",
        help_text="Number of payment attempts made (including the initial failure).",
    )
    first_failed_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="First Failed At",
        help_text="When the initial payment failure occurred.",
    )
    next_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Next Retry At",
        help_text="Scheduled datetime for the next retry attempt.",
    )
    last_attempt_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Last Attempt At",
        help_text="When the most recent retry was attempted.",
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
        verbose_name="Status",
    )
    stripe_invoice_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Invoice ID",
        help_text="The Stripe invoice that failed.",
    )
    stripe_subscription_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Stripe Subscription ID",
        help_text="The Stripe subscription associated with this dunning record.",
    )
    failure_reason = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Failure Reason",
        help_text="The last payment failure reason from Stripe.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        verbose_name="Notes",
        help_text="Internal notes about this dunning record.",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Resolved At",
        help_text="When this dunning record was resolved (payment recovered or policy cancelled).",
    )

    class Meta:
        db_table = "dunning_records"
        verbose_name = "Dunning Record"
        verbose_name_plural = "Dunning Records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
        ]

    def __str__(self):
        return f"DunningRecord #{self.pk} — {self.policy.policy_number} attempt {self.attempt_count} ({self.status})"

    def get_next_retry_day_offset(self) -> int | None:
        """Return the number of days from first_failed_at for the next retry, or None if max reached."""
        if self.attempt_count <= len(self.RETRY_DAYS):
            return self.RETRY_DAYS[self.attempt_count - 1]
        return None

    def schedule_next_retry(self):
        """Set next_retry_at based on attempt_count and first_failed_at."""
        from datetime import timedelta

        day_offset = self.get_next_retry_day_offset()
        if day_offset is not None:
            self.next_retry_at = self.first_failed_at + timedelta(days=day_offset)
        else:
            self.next_retry_at = None
