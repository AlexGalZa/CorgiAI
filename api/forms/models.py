"""
Form builder models for dynamic coverage questionnaires.

``FormDefinition`` stores the schema for a coverage questionnaire including
field definitions, conditional display logic, and mappings to rating engine
inputs. Multiple versions of the same form can coexist; only the active one
is served to the frontend.
"""

from __future__ import annotations

from django.db import models

from common.models import TimestampedModel


class FormDefinition(TimestampedModel):
    """A versioned, dynamic form definition for coverage questionnaires.

    Each form definition corresponds to a coverage type (or is generic)
    and contains:
    - ``fields``: An ordered array of field definitions (label, type, validation).
    - ``conditional_logic``: Rules for showing/hiding fields based on other answers.
    - ``rating_field_mappings``: Maps form field keys to rating engine input keys.

    Attributes:
        name: Human-readable name of the form (e.g. "Cyber Liability Questionnaire").
        slug: URL-safe unique identifier.
        version: Integer version number; allows side-by-side migration.
        description: Optional description for admin reference.
        fields: JSON array of field definition objects.
        conditional_logic: JSON object describing show/hide rules.
        rating_field_mappings: JSON object mapping form field keys → rating input keys.
        coverage_type: Optional slug linking this form to a coverage type.
        is_active: Whether this form version is currently served.
    """

    name = models.CharField(
        max_length=255,
        verbose_name="Form Name",
        help_text="Human-readable name of this form definition",
    )
    slug = models.SlugField(
        max_length=100,
        verbose_name="Slug",
        help_text="URL-safe unique identifier for this form",
    )
    version = models.PositiveIntegerField(
        default=1,
        verbose_name="Version",
        help_text="Form version number (increment when making breaking changes)",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="Description",
        help_text="Internal description of this form definition",
    )
    fields = models.JSONField(
        default=list,
        verbose_name="Field Definitions",
        help_text=(
            "Ordered array of field objects. Each field: "
            '{"key": "str", "label": "str", "field_type": "text|number|select|...", '
            '"required": bool, "options": [...], "validation": {...}}'
        ),
    )
    conditional_logic = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Conditional Logic",
        help_text=(
            'Show/hide rules keyed by target field. Example: {"field_b": {"depends_on": "field_a", "show_when": "yes"}}'
        ),
    )
    rating_field_mappings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Rating Field Mappings",
        help_text=(
            "Maps form field keys to rating engine input keys. "
            'Example: {"employee_band": "employee_count", "revenue": "revenue"}'
        ),
    )
    coverage_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Coverage Type",
        help_text="Coverage slug this form is tied to (null = generic/reusable form)",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Only the active version of a slug is served to the frontend",
    )

    class Meta:
        db_table = "form_definitions"
        verbose_name = "Form Definition"
        verbose_name_plural = "Form Definitions"
        ordering = ["name", "-version"]
        unique_together = ["slug", "version"]
        indexes = [
            models.Index(fields=["slug", "is_active"]),
            models.Index(fields=["coverage_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version}"


class FormSubmission(TimestampedModel):
    """Stores submitted form data per quote + form definition."""

    form_definition = models.ForeignKey(
        FormDefinition,
        on_delete=models.PROTECT,
        related_name="submissions",
        verbose_name="Form Definition",
        help_text="The form definition this submission is for",
    )
    quote = models.ForeignKey(
        "quotes.Quote",
        on_delete=models.CASCADE,
        related_name="form_submissions",
        verbose_name="Quote",
        help_text="The quote this form submission belongs to",
    )
    data = models.JSONField(
        default=dict,
        verbose_name="Submitted Data",
        help_text="JSON object containing the submitted form field values",
    )
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Submitted At",
        help_text="Timestamp when the form was submitted",
    )

    class Meta:
        db_table = "form_submissions"
        verbose_name = "Form Submission"
        verbose_name_plural = "Form Submissions"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["quote", "form_definition"]),
        ]

    def __str__(self) -> str:
        return f"{self.form_definition.name} submission for {self.quote}"
