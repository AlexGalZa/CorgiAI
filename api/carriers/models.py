"""
Carrier management models for the Corgi Insurance platform.

Tracks insurance carriers we work with, their appetites, ratings, and contacts.
"""

from django.db import models

from common.models import TimestampedModel


class Carrier(TimestampedModel):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name="Carrier Name",
        help_text="Legal name of the insurance carrier",
    )
    am_best_rating = models.CharField(
        max_length=10,
        blank=True,
        verbose_name="AM Best Rating",
        help_text="AM Best financial strength rating (e.g. A, A+, A-)",
    )
    appetite_description = models.TextField(
        blank=True,
        verbose_name="Appetite Description",
        help_text="Description of the carrier's underwriting appetite and preferred risks",
    )
    commission_rates = models.JSONField(
        default=dict,
        verbose_name="Commission Rates",
        help_text='JSON object mapping coverage types to commission rates, e.g. {"tech-eo": 0.15, "cyber": 0.12}',
    )
    contact_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Contact Name",
        help_text="Primary contact person at the carrier",
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name="Contact Email",
    )
    contact_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="Contact Phone",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="active",
        db_index=True,
        verbose_name="Status",
    )
    notes = models.TextField(
        blank=True,
        verbose_name="Internal Notes",
    )

    class Meta:
        db_table = "carriers"
        verbose_name = "Carrier"
        verbose_name_plural = "Carriers"
        ordering = ["name"]

    def __str__(self):
        rating = f" [{self.am_best_rating}]" if self.am_best_rating else ""
        return f"{self.name}{rating}"
