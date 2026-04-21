"""Add soft-delete fields (is_deleted, deleted_at) to Policy model."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0027_add_performance_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="policy",
            name="is_deleted",
            field=models.BooleanField(
                default=False,
                db_index=True,
                verbose_name="Is Deleted",
                help_text="Soft-delete flag. True means the record is logically deleted.",
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="deleted_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                verbose_name="Deleted At",
                help_text="Timestamp when this record was soft-deleted",
            ),
        ),
    ]
