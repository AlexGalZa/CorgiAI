from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0029_add_available_coverages"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="initial_ai_classifications",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="First AI classification results per coverage (preserved across recalculations)",
                null=True,
                verbose_name="Initial AI Classifications",
            ),
        ),
    ]
