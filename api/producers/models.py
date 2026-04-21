from django.db import models

from common.models import TimestampedModel
from policies.models import Policy


class CommissionPayout(TimestampedModel):
    """Tracks commission payouts owed to producers based on policy premiums."""

    CALCULATION_METHOD_CHOICES = [
        ("percentage_of_premium", "Percentage of Premium"),
        ("flat_fee", "Flat Fee"),
        ("tiered", "Tiered Rate"),
    ]

    STATUS_CHOICES = [
        ("calculated", "Calculated"),
        ("approved", "Approved"),
        ("paid", "Paid"),
        ("reversed", "Reversed"),
    ]

    producer = models.ForeignKey(
        "Producer",
        on_delete=models.PROTECT,
        related_name="commission_payouts",
        verbose_name="Producer",
    )
    policy = models.ForeignKey(
        Policy,
        on_delete=models.PROTECT,
        related_name="commission_payouts",
        verbose_name="Policy",
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        verbose_name="Payout Amount",
        help_text="Commission payout amount in USD",
    )
    calculation_method = models.CharField(
        max_length=30,
        choices=CALCULATION_METHOD_CHOICES,
        default="percentage_of_premium",
        verbose_name="Calculation Method",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="calculated",
        db_index=True,
        verbose_name="Status",
    )
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Paid At",
        help_text="Timestamp when the payout was marked as paid",
    )
    stripe_transfer_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Stripe Transfer ID",
        help_text="Stripe Connect transfer ID if paid via Stripe",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Notes",
        help_text="Internal notes about this payout",
    )
    reversal_reason = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Reversal Reason",
        help_text="Populated when status='reversed' (e.g., 'policy_cancelled')",
    )
    reversed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Reversed At",
        help_text="Timestamp when this payout was reversed",
    )
    period_start = models.DateField(
        null=True,
        blank=True,
        verbose_name="Period Start",
        help_text="Start of the accrual period this payout covers (for monthly payouts)",
    )
    period_end = models.DateField(
        null=True,
        blank=True,
        verbose_name="Period End",
        help_text="End of the accrual period this payout covers (for monthly payouts)",
    )

    class Meta:
        db_table = "commission_payouts"
        verbose_name = "Commission Payout"
        verbose_name_plural = "Commission Payouts"
        ordering = ["-created_at"]

    def __str__(self):
        return f"${self.amount} to {self.producer.name} for {self.policy.policy_number} [{self.status}]"


class Producer(TimestampedModel):
    PRODUCER_TYPE_CHOICES = [
        ("bdr", "BDR"),
        ("ae", "AE"),
        ("am", "AM"),
        ("broker", "Broker"),
        ("agent", "Agent"),
    ]

    name = models.CharField(
        max_length=255,
        verbose_name="Name",
        help_text="Full name of the producer",
    )
    producer_type = models.CharField(
        max_length=20,
        choices=PRODUCER_TYPE_CHOICES,
        verbose_name="Producer Type",
        help_text="Type of producer role",
    )
    email = models.EmailField(
        blank=True,
        verbose_name="Email",
        help_text="Producer's email address",
    )
    license_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="License Number",
        help_text="Insurance producer license number",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Is Active",
        help_text="Whether this producer is currently active",
    )

    class Meta:
        db_table = "producers"
        verbose_name = "Producer"
        verbose_name_plural = "Producers"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_producer_type_display()})"


class PolicyProducer(TimestampedModel):
    COMMISSION_TYPE_CHOICES = [
        ("percentage", "Percentage of GWP"),
        ("flat", "Flat Fee"),
    ]

    policy = models.ForeignKey(
        Policy,
        on_delete=models.CASCADE,
        related_name="producers",
    )
    producer = models.ForeignKey(
        Producer,
        on_delete=models.PROTECT,
        related_name="policy_assignments",
    )
    commission_type = models.CharField(
        max_length=20,
        choices=COMMISSION_TYPE_CHOICES,
        default="percentage",
    )
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Commission rate as decimal (e.g., 0.1500 for 15%)",
    )
    commission_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Flat fee commission amount, or calculated amount for percentage",
    )

    class Meta:
        db_table = "policy_producers"
        verbose_name = "Policy Producer"
        verbose_name_plural = "Policy Producers"
        unique_together = ["policy", "producer"]

    def __str__(self):
        return f"{self.producer.name} on {self.policy.policy_number}"
