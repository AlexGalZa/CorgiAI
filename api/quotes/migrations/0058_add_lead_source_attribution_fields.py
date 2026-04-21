from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0057_company_dba_name_company_naics_code_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="utm_source",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Traffic source captured from the utm_source query param (e.g. 'google', 'linkedin')",
                max_length=64,
                verbose_name="UTM Source",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="utm_medium",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Traffic medium captured from the utm_medium query param (e.g. 'cpc', 'email')",
                max_length=64,
                verbose_name="UTM Medium",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="utm_campaign",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Campaign identifier captured from the utm_campaign query param",
                max_length=128,
                verbose_name="UTM Campaign",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="referrer_url",
            field=models.TextField(
                blank=True,
                default="",
                help_text="document.referrer value at the time the quote was created",
                verbose_name="Referrer URL",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="landing_page_url",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Initial landing page URL (including query string) where the visitor was acquired",
                verbose_name="Landing Page URL",
            ),
        ),
    ]
