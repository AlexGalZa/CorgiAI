import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("external_api", "0004_move_models_to_api_keys"),
        ("organizations", "0003_create_personal_orgs"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="ApiKey",
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
                                auto_now_add=True, verbose_name="Created At"
                            ),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(
                                auto_now=True, verbose_name="Updated At"
                            ),
                        ),
                        ("name", models.CharField(max_length=255, verbose_name="Name")),
                        (
                            "prefix",
                            models.CharField(
                                max_length=16, unique=True, verbose_name="Prefix"
                            ),
                        ),
                        (
                            "key_hash",
                            models.CharField(max_length=64, verbose_name="Key Hash"),
                        ),
                        (
                            "is_active",
                            models.BooleanField(default=True, verbose_name="Active"),
                        ),
                        (
                            "last_used_at",
                            models.DateTimeField(
                                blank=True, null=True, verbose_name="Last Used At"
                            ),
                        ),
                        (
                            "organization",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="api_keys",
                                to="organizations.organization",
                                verbose_name="Organization",
                            ),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="created_api_keys",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Created By",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "API Key",
                        "verbose_name_plural": "API Keys",
                        "db_table": "external_api_keys",
                        "ordering": ["-created_at"],
                    },
                ),
                migrations.CreateModel(
                    name="ApiKeyInvite",
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
                                auto_now_add=True, verbose_name="Created At"
                            ),
                        ),
                        (
                            "updated_at",
                            models.DateTimeField(
                                auto_now=True, verbose_name="Updated At"
                            ),
                        ),
                        (
                            "token",
                            models.CharField(
                                max_length=64, unique=True, verbose_name="Token"
                            ),
                        ),
                        (
                            "expires_at",
                            models.DateTimeField(
                                blank=True, null=True, verbose_name="Expires At"
                            ),
                        ),
                        (
                            "is_used",
                            models.BooleanField(default=False, verbose_name="Used"),
                        ),
                        (
                            "used_at",
                            models.DateTimeField(
                                blank=True, null=True, verbose_name="Used At"
                            ),
                        ),
                        (
                            "partner_first_name",
                            models.CharField(blank=True, default="", max_length=150),
                        ),
                        (
                            "partner_last_name",
                            models.CharField(blank=True, default="", max_length=150),
                        ),
                        (
                            "partner_org_name",
                            models.CharField(blank=True, default="", max_length=255),
                        ),
                        ("partner_email", models.EmailField(blank=True, default="")),
                        (
                            "api_key",
                            models.OneToOneField(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="invite",
                                to="api_keys.apikey",
                                verbose_name="API Key",
                            ),
                        ),
                        (
                            "created_by",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="created_api_key_invites",
                                to=settings.AUTH_USER_MODEL,
                                verbose_name="Created By",
                            ),
                        ),
                    ],
                    options={
                        "verbose_name": "API Key Invite",
                        "verbose_name_plural": "API Key Invites",
                        "db_table": "external_api_key_invites",
                        "ordering": ["-created_at"],
                    },
                ),
            ],
            database_operations=[],
        ),
    ]
