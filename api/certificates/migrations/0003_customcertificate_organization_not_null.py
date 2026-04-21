from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("certificates", "0002_customcertificate_organization"),
        ("organizations", "0003_create_personal_orgs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="customcertificate",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="custom_certificates",
                to="organizations.organization",
            ),
        ),
    ]
