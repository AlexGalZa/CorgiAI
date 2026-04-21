"""Add CoverageType and PromoCode models."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quotes", "0050_add_referral_partner_notification_emails"),
    ]

    operations = [
        migrations.CreateModel(
            name="CoverageType",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this record was created",
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when this record was last updated",
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Unique identifier slug (e.g. 'cyber-liability', 'custom-workers-comp')",
                        max_length=60,
                        unique=True,
                        verbose_name="Slug",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human-readable display name",
                        max_length=255,
                        verbose_name="Name",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("instant", "Instant (RRG-rated, bound online)"),
                            (
                                "brokered_form",
                                "Brokered with Form (extra questionnaire)",
                            ),
                            ("brokered_intent", "Brokered Intent-Only (no extra form)"),
                        ],
                        db_index=True,
                        help_text="Coverage tier: instant (rated by Corgi engine), brokered_form, or brokered_intent",
                        max_length=20,
                        verbose_name="Tier",
                    ),
                ),
                (
                    "carrier_default",
                    models.CharField(
                        blank=True,
                        help_text="Default insurance carrier for this coverage type",
                        max_length=255,
                        null=True,
                        verbose_name="Default Carrier",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether this coverage type is currently available for selection",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        help_text="Optional description of this coverage type",
                        null=True,
                        verbose_name="Description",
                    ),
                ),
                (
                    "display_order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Order in which to display this coverage type in the UI",
                        verbose_name="Display Order",
                    ),
                ),
            ],
            options={
                "db_table": "coverage_types",
                "verbose_name": "Coverage Type",
                "verbose_name_plural": "Coverage Types",
                "ordering": ["display_order", "name"],
            },
        ),
        migrations.CreateModel(
            name="PromoCode",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this record was created",
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when this record was last updated",
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        db_index=True,
                        help_text="Promotional code string (case-insensitive)",
                        max_length=50,
                        unique=True,
                        verbose_name="Code",
                    ),
                ),
                (
                    "stripe_coupon_id",
                    models.CharField(
                        blank=True,
                        help_text="Associated Stripe coupon ID for payment processing",
                        max_length=255,
                        null=True,
                        verbose_name="Stripe Coupon ID",
                    ),
                ),
                (
                    "discount_type",
                    models.CharField(
                        choices=[
                            ("percentage", "Percentage"),
                            ("fixed", "Fixed Amount"),
                        ],
                        help_text="Type of discount: percentage or fixed amount",
                        max_length=10,
                        verbose_name="Discount Type",
                    ),
                ),
                (
                    "discount_value",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Discount amount (percentage value like 20.00 for 20%%, or fixed dollar amount)",
                        max_digits=10,
                        verbose_name="Discount Value",
                    ),
                ),
                (
                    "valid_from",
                    models.DateTimeField(
                        blank=True,
                        help_text="Start of the promotional period (null = immediately valid)",
                        null=True,
                        verbose_name="Valid From",
                    ),
                ),
                (
                    "valid_until",
                    models.DateTimeField(
                        blank=True,
                        help_text="End of the promotional period (null = no expiration)",
                        null=True,
                        verbose_name="Valid Until",
                    ),
                ),
                (
                    "max_uses",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Maximum number of times this code can be redeemed (null = unlimited)",
                        null=True,
                        verbose_name="Max Uses",
                    ),
                ),
                (
                    "use_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Number of times this code has been redeemed",
                        verbose_name="Use Count",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Whether this promo code is currently usable",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Admin who created this promo code",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_promo_codes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created By",
                    ),
                ),
            ],
            options={
                "db_table": "promo_codes",
                "verbose_name": "Promo Code",
                "verbose_name_plural": "Promo Codes",
                "ordering": ["-created_at"],
            },
        ),
    ]
