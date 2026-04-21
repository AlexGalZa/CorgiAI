# Generated manually for policy refactor: 1 coverage = 1 policy

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0001_initial"),
        ("policies", "0005_delete_policydocument"),
    ]

    operations = [
        # Create PolicySequence table
        migrations.CreateModel(
            name="PolicySequence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("lob_code", models.CharField(max_length=2)),
                ("state", models.CharField(max_length=2)),
                ("year", models.IntegerField()),
                ("last_sequence", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "policy_sequences",
                "unique_together": {("lob_code", "state", "year")},
            },
        ),
        # Create COISequence table
        migrations.CreateModel(
            name="COISequence",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("state", models.CharField(max_length=2)),
                ("year", models.IntegerField()),
                ("last_sequence", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "coi_sequences",
                "unique_together": {("state", "year")},
            },
        ),
        # Add coverage_type field to Policy
        migrations.AddField(
            model_name="policy",
            name="coverage_type",
            field=models.CharField(
                blank=True,
                default="",
                help_text="The specific coverage type for this policy",
                max_length=50,
                verbose_name="Coverage Type",
            ),
        ),
        # Add coi_number field to Policy
        migrations.AddField(
            model_name="policy",
            name="coi_number",
            field=models.CharField(
                blank=True,
                help_text="Certificate of Insurance number shared by policies from same purchase",
                max_length=20,
                null=True,
                verbose_name="COI Number",
            ),
        ),
        # Add limits_retentions field to Policy
        migrations.AddField(
            model_name="policy",
            name="limits_retentions",
            field=models.JSONField(
                default=dict,
                help_text="Limits and retention amounts for this specific policy/coverage",
                verbose_name="Limits & Retentions",
            ),
        ),
        # Change policy_number max_length from 20 to 25
        migrations.AlterField(
            model_name="policy",
            name="policy_number",
            field=models.CharField(
                max_length=25, unique=True, verbose_name="Policy Number"
            ),
        ),
        # Change quote from OneToOneField to ForeignKey
        migrations.AlterField(
            model_name="policy",
            name="quote",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="policies",
                to="quotes.quote",
                verbose_name="Quote",
            ),
        ),
    ]
