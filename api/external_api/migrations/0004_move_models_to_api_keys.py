from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("external_api", "0003_add_invite_nullable_org"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.DeleteModel("ApiKeyInvite"),
                migrations.DeleteModel("ApiKey"),
            ],
            database_operations=[],
        ),
    ]
