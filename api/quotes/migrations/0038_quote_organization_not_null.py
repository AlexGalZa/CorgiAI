from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0037_quote_organization"),
        ("organizations", "0003_create_personal_orgs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quote",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="quotes",
                to="organizations.organization",
            ),
        ),
    ]
