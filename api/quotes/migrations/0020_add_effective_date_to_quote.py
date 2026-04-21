from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0019_alter_customproduct_product_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="effective_date",
            field=models.DateField(
                blank=True,
                help_text="Requested policy effective date",
                null=True,
                verbose_name="Effective Date",
            ),
        ),
    ]
