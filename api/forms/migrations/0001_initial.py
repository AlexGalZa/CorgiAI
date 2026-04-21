"""Initial migration for forms app: FormDefinition and FormSubmission."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("quotes", "0050_add_referral_partner_notification_emails"),
    ]

    operations = [
        migrations.CreateModel(
            name="FormDefinition",
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
                    "name",
                    models.CharField(
                        help_text="Human-readable name of this form definition",
                        max_length=255,
                        verbose_name="Form Name",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="URL-safe unique identifier for this form",
                        max_length=100,
                        verbose_name="Slug",
                    ),
                ),
                (
                    "version",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Form version number (increment when making breaking changes)",
                        verbose_name="Version",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Internal description of this form definition",
                        verbose_name="Description",
                    ),
                ),
                (
                    "fields",
                    models.JSONField(
                        default=list,
                        help_text='Ordered array of field objects. Each field: {"key": "str", "label": "str", "field_type": "text|number|select|...", "required": bool, "options": [...], "validation": {...}}',
                        verbose_name="Field Definitions",
                    ),
                ),
                (
                    "conditional_logic",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Show/hide rules keyed by target field. Example: {"field_b": {"depends_on": "field_a", "show_when": "yes"}}',
                        verbose_name="Conditional Logic",
                    ),
                ),
                (
                    "rating_field_mappings",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Maps form field keys to rating engine input keys. Example: {"employee_band": "employee_count", "revenue": "revenue"}',
                        verbose_name="Rating Field Mappings",
                    ),
                ),
                (
                    "coverage_type",
                    models.CharField(
                        blank=True,
                        help_text="Coverage slug this form is tied to (null = generic/reusable form)",
                        max_length=50,
                        null=True,
                        verbose_name="Coverage Type",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Only the active version of a slug is served to the frontend",
                        verbose_name="Active",
                    ),
                ),
            ],
            options={
                "db_table": "form_definitions",
                "verbose_name": "Form Definition",
                "verbose_name_plural": "Form Definitions",
                "ordering": ["name", "-version"],
            },
        ),
        migrations.AddConstraint(
            model_name="formdefinition",
            constraint=models.UniqueConstraint(
                fields=["slug", "version"], name="unique_form_slug_version"
            ),
        ),
        migrations.AddIndex(
            model_name="formdefinition",
            index=models.Index(
                fields=["slug", "is_active"], name="form_defini_slug_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="formdefinition",
            index=models.Index(
                fields=["coverage_type"], name="form_defini_coverage_type_idx"
            ),
        ),
        migrations.CreateModel(
            name="FormSubmission",
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
                    "data",
                    models.JSONField(
                        default=dict,
                        help_text="JSON object containing the submitted form field values",
                        verbose_name="Submitted Data",
                    ),
                ),
                (
                    "submitted_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the form was submitted",
                        verbose_name="Submitted At",
                    ),
                ),
                (
                    "form_definition",
                    models.ForeignKey(
                        help_text="The form definition this submission is for",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="submissions",
                        to="forms.formdefinition",
                        verbose_name="Form Definition",
                    ),
                ),
                (
                    "quote",
                    models.ForeignKey(
                        help_text="The quote this form submission belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="form_submissions",
                        to="quotes.quote",
                        verbose_name="Quote",
                    ),
                ),
            ],
            options={
                "db_table": "form_submissions",
                "verbose_name": "Form Submission",
                "verbose_name_plural": "Form Submissions",
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.AddIndex(
            model_name="formsubmission",
            index=models.Index(
                fields=["quote", "form_definition"], name="form_sub_quote_formdef_idx"
            ),
        ),
    ]
