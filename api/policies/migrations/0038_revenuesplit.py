from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0037_policytransaction_stripe_payout_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="RevenueSplit",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when this record was created",
                        verbose_name="Created At",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when this record was last updated",
                        verbose_name="Updated At",
                    ),
                ),
                (
                    "corgi_admin",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Dollars allocated to the Corgi Admin bucket.",
                        max_digits=10,
                        verbose_name="Corgi Admin",
                    ),
                ),
                (
                    "techrrg",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Dollars allocated to TechRRG (includes collected tax on non-brokered policies).",
                        max_digits=10,
                        verbose_name="TechRRG",
                    ),
                ),
                (
                    "corgire",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Dollars allocated to the CorgiRe reinsurance bucket.",
                        max_digits=10,
                        verbose_name="CorgiRe",
                    ),
                ),
                (
                    "dane",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Dollars allocated to the Dane override bucket.",
                        max_digits=10,
                        verbose_name="Dane",
                    ),
                ),
                (
                    "admin_fee",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Policy / admin fees routed outside the premium split.",
                        max_digits=10,
                        verbose_name="Admin Fee",
                    ),
                ),
                (
                    "computed_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the split was computed.",
                        verbose_name="Computed At",
                    ),
                ),
                (
                    "transaction",
                    models.ForeignKey(
                        help_text="Transaction this revenue split was computed from.",
                        on_delete=models.deletion.CASCADE,
                        related_name="revenue_splits",
                        to="policies.policytransaction",
                        verbose_name="Policy Transaction",
                    ),
                ),
            ],
            options={
                "verbose_name": "Revenue Split",
                "verbose_name_plural": "Revenue Splits",
                "db_table": "revenue_splits",
                "ordering": ["-computed_at"],
            },
        ),
        migrations.AddIndex(
            model_name="revenuesplit",
            index=models.Index(
                fields=["transaction", "computed_at"],
                name="revenue_spl_transac_computed_idx",
            ),
        ),
    ]
