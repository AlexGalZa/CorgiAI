"""Add failed_login_attempts and locked_until fields for account lockout."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0014_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="failed_login_attempts",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="user",
            name="locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
