"""Add avatar_url, timezone, notification_preferences to User."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0010_create_corgi_admin_groups"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="avatar_url",
            field=models.URLField(
                blank=True,
                help_text="URL to the user's avatar image",
                max_length=500,
                null=True,
                verbose_name="Avatar URL",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="timezone",
            field=models.CharField(
                blank=True,
                help_text="User's preferred timezone (e.g. 'America/New_York')",
                max_length=50,
                null=True,
                verbose_name="Timezone",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="notification_preferences",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="User notification settings: {email_quotes, email_claims, email_billing, push_enabled}",
                verbose_name="Notification Preferences",
            ),
        ),
    ]
