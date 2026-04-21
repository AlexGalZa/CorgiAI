"""Add soft-delete fields (is_deleted, deleted_at) to Quote model."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0053_add_business_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="is_deleted",
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name="Is Deleted",
                help_text="Soft-delete flag. True means the record is logically deleted.",
            ),
        ),
        migrations.AddField(
            model_name="quote",
            name="deleted_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name="Deleted At",
                help_text="Timestamp when this record was soft-deleted",
            ),
        ),
    ]
