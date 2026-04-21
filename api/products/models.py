"""
Product configuration models for Corgi Insurance.

Allows non-developers to adjust product settings (limits, retentions, rating tiers)
via the Django admin without code changes.
"""

from django.db import models

from common.models import TimestampedModel


class ProductConfiguration(TimestampedModel):
    """
    Configuration for an insurance product (coverage type).
    Allows admins to adjust product settings without code deploys.
    """

    RATING_TIER_CHOICES = [
        ("tier1_instant", "Tier 1 — Instant Quote"),
        ("tier2_brokered_form", "Tier 2 — Brokered with Form"),
        ("tier3_brokered_intent", "Tier 3 — Brokered Intent Only"),
    ]

    coverage_type = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name="Coverage Type Slug",
        help_text="Internal coverage type slug (e.g. 'commercial-general-liability')",
    )
    display_name = models.CharField(
        max_length=255,
        verbose_name="Display Name",
        help_text="Human-readable product name shown to customers",
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description",
        help_text="Short product description shown in the portal",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Active",
        help_text="Whether this product is available for purchase",
    )
    min_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Minimum Limit ($)",
        help_text="Minimum available aggregate limit in dollars",
    )
    max_limit = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Maximum Limit ($)",
        help_text="Maximum available aggregate limit in dollars",
    )
    available_retentions = models.JSONField(
        default=list,
        verbose_name="Available Retentions",
        help_text="List of available retention/deductible options in dollars, e.g. [500, 1000, 2500]",
    )
    rating_tier = models.CharField(
        max_length=30,
        choices=RATING_TIER_CHOICES,
        default="tier1_instant",
        verbose_name="Rating Tier",
        help_text="How premiums are calculated for this product",
    )
    requires_review = models.BooleanField(
        default=False,
        verbose_name="Requires Underwriter Review",
        help_text="If true, all quotes for this product will go to needs_review status",
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes",
        help_text="Internal notes for underwriters / product team",
    )
    is_brokered_variant = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Brokered Variant",
        help_text=(
            "True if this ProductConfiguration is the BROKERED sibling of a "
            "direct product (used when limit > $5M or other >5M brokered routing)."
        ),
    )
    parent_variant = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="brokered_children",
        on_delete=models.SET_NULL,
        verbose_name="Parent Variant",
        help_text=(
            "Link from a brokered variant back to its direct (non-brokered) twin. Null on the direct product itself."
        ),
    )

    class Meta:
        db_table = "product_configurations"
        verbose_name = "Product Configuration"
        verbose_name_plural = "Product Configurations"
        ordering = ["display_name"]

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.display_name} ({self.coverage_type}) [{status}]"
