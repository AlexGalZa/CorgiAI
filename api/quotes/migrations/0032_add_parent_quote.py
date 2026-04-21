from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0031_alter_quote_quote_amount"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="parent_quote",
            field=models.ForeignKey(
                blank=True,
                help_text="For split quotes: links to the original quote this was split from",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="child_quotes",
                to="quotes.quote",
                verbose_name="Parent Quote",
            ),
        ),
    ]
