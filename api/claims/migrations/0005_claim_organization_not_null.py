from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0004_claim_organization"),
        ("organizations", "0003_create_personal_orgs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="claim",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="claims",
                to="organizations.organization",
            ),
        ),
    ]
