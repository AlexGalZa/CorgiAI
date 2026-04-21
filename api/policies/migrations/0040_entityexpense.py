from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0039_policy_signed_agreement_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="EntityExpense",
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
                    "entity",
                    models.CharField(
                        choices=[
                            ("corgi_admin", "Corgi Admin"),
                            ("techrrg", "TechRRG"),
                            ("corgire", "CorgiRe"),
                            ("dane", "Dane"),
                        ],
                        db_index=True,
                        help_text="Legal entity this expense is booked against.",
                        max_length=20,
                        verbose_name="Entity",
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Dollars spent (cash outflow).",
                        max_digits=15,
                        verbose_name="Amount",
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        db_index=True,
                        help_text="Expense category (e.g. payroll, vendor, insurance, software).",
                        max_length=50,
                        verbose_name="Category",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable description of the expense.",
                        verbose_name="Description",
                    ),
                ),
                (
                    "incurred_at",
                    models.DateField(
                        db_index=True,
                        help_text="Date the expense was incurred.",
                        verbose_name="Incurred At",
                    ),
                ),
            ],
            options={
                "verbose_name": "Entity Expense",
                "verbose_name_plural": "Entity Expenses",
                "db_table": "entity_expenses",
                "ordering": ["-incurred_at"],
            },
        ),
        migrations.AddIndex(
            model_name="entityexpense",
            index=models.Index(
                fields=["entity", "incurred_at"], name="entity_expe_entity_49f749_idx"
            ),
        ),
    ]
