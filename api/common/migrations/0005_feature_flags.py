"""
Migration: add FeatureFlag model and seed common flags.
"""

from django.db import migrations, models


def seed_feature_flags(apps, schema_editor):
    FeatureFlag = apps.get_model("common", "FeatureFlag")

    seeds = [
        {
            "key": "new_portal_dashboard",
            "description": "Enable the redesigned V3 portal dashboard with KPI cards and pipeline view.",
            "is_enabled": False,
            "rollout_percentage": 0,
            "staff_only": False,
        },
        {
            "key": "renewal_flow",
            "description": "Enable the automated renewal flow with email triggers and proposal generation.",
            "is_enabled": False,
            "rollout_percentage": 0,
            "staff_only": False,
        },
        {
            "key": "self_serve_limits",
            "description": "Allow customers to self-serve limit and retention changes without underwriter approval.",
            "is_enabled": False,
            "rollout_percentage": 0,
            "staff_only": False,
        },
        {
            "key": "slack_notifications",
            "description": "Send Slack notifications for key events (quote ready, claim filed, payment failed).",
            "is_enabled": False,
            "rollout_percentage": 0,
            "staff_only": True,
        },
    ]

    for seed in seeds:
        FeatureFlag.objects.get_or_create(key=seed["key"], defaults=seed)


class Migration(migrations.Migration):
    dependencies = [
        ("common", "0004_add_compliance_deadline"),
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeatureFlag",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "key",
                    models.CharField(
                        db_index=True,
                        help_text="Unique identifier, e.g. 'new_portal_dashboard'",
                        max_length=100,
                        unique=True,
                        verbose_name="Flag Key",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable description of what this flag controls",
                        verbose_name="Description",
                    ),
                ),
                (
                    "is_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="Master switch — if False, flag is off for everyone",
                        verbose_name="Enabled",
                    ),
                ),
                (
                    "rollout_percentage",
                    models.PositiveSmallIntegerField(
                        default=0,
                        help_text="0 = nobody, 100 = everyone (within enabled scope). Deterministic by user/org ID hash.",
                        verbose_name="Rollout %",
                    ),
                ),
                (
                    "allowed_orgs",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Orgs explicitly allowlisted regardless of rollout %",
                        related_name="feature_flags",
                        to="organizations.organization",
                        verbose_name="Allowed Orgs",
                    ),
                ),
                (
                    "staff_only",
                    models.BooleanField(
                        default=False,
                        help_text="If True, only staff (is_staff=True) users can see this feature",
                        verbose_name="Staff Only",
                    ),
                ),
            ],
            options={
                "verbose_name": "Feature Flag",
                "verbose_name_plural": "Feature Flags",
                "ordering": ["key"],
            },
        ),
        # Seed common flags
        migrations.RunPython(
            code=seed_feature_flags,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
