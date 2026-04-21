"""Add status, revoked_at, revoked_by to CustomCertificate."""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("certificates", "0003_customcertificate_organization_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="customcertificate",
            name="status",
            field=models.CharField(
                choices=[
                    ("active", "Active"),
                    ("revoked", "Revoked"),
                    ("expired", "Expired"),
                ],
                db_index=True,
                default="active",
                help_text="Current status of this certificate",
                max_length=10,
                verbose_name="Status",
            ),
        ),
        migrations.AddField(
            model_name="customcertificate",
            name="revoked_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when this certificate was revoked",
                null=True,
                verbose_name="Revoked At",
            ),
        ),
        migrations.AddField(
            model_name="customcertificate",
            name="revoked_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who revoked this certificate",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="revoked_certificates",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Revoked By",
            ),
        ),
    ]
