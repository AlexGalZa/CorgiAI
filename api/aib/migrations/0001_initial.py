import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("quotes", "0058_add_lead_source_attribution_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AibSession",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("session_token", models.CharField(default=uuid.uuid4, max_length=36, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="aib_sessions", to=settings.AUTH_USER_MODEL)),
                ("quote", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="aib_sessions", to="quotes.quote")),
            ],
            options={"db_table": "aib_session", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AibMessage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("user", "User"), ("assistant", "Assistant")], max_length=10)),
                ("content", models.TextField()),
                ("extracted_fields", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="aib.aibsession")),
            ],
            options={"db_table": "aib_message", "ordering": ["created_at"]},
        ),
    ]
