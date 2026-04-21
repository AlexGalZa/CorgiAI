from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_userdocument_organization"),
        ("organizations", "0003_create_personal_orgs"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userdocument",
            name="organization",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="user_documents",
                to="organizations.organization",
            ),
        ),
    ]
