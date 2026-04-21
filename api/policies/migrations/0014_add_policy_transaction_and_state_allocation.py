from decimal import Decimal

from django.db import migrations, models
import django.db.models.deletion


def backfill_transactions_and_allocations(apps, schema_editor):
    """
    Create PolicyTransaction and StateAllocation records for existing policies.

    For each policy:
    - Creates one PolicyTransaction (type='new')
    - Creates one StateAllocation (100% to HQ state)
    - Calculates GWP and tax using STATE_TAX_RATES
    """
    # Import here to avoid issues during migration
    from rating.constants import STATE_TAX_RATES

    Policy = apps.get_model("policies", "Policy")
    PolicyTransaction = apps.get_model("policies", "PolicyTransaction")
    StateAllocation = apps.get_model("policies", "StateAllocation")

    policies = Policy.objects.select_related("quote__company__business_address").all()

    for policy in policies:
        # Get HQ state
        try:
            state = policy.quote.company.business_address.state
        except AttributeError:
            # Skip if missing related data
            print(f"Skipping policy {policy.id} - missing address data")
            continue

        if not state:
            print(f"Skipping policy {policy.id} - no state")
            continue

        # Calculate GWP and tax
        tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        total_premium = policy.premium
        gwp = (total_premium / tax_multiplier).quantize(Decimal("0.01"))
        tax_amount = (total_premium - gwp).quantize(Decimal("0.01"))

        # Create transaction
        transaction = PolicyTransaction.objects.create(
            policy=policy,
            transaction_type="new",
            effective_date=policy.effective_date,
            accounting_date=policy.purchased_at.date()
            if policy.purchased_at
            else policy.effective_date,
            gross_written_premium=gwp,
            tax_amount=tax_amount,
        )

        # Create state allocation (100% to HQ state)
        StateAllocation.objects.create(
            transaction=transaction,
            state=state,
            allocation_method="hq",
            allocation_percent=Decimal("100.00"),
            allocated_premium=gwp,
        )

    print(f"Backfilled {policies.count()} policies with transactions and allocations")


def reverse_backfill(apps, schema_editor):
    """Remove all backfilled data."""
    PolicyTransaction = apps.get_model("policies", "PolicyTransaction")
    # Cascade delete will remove StateAllocations
    PolicyTransaction.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0013_refactor_payment_stripe_id"),
    ]

    operations = [
        # Create PolicyTransaction table
        migrations.CreateModel(
            name="PolicyTransaction",
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
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("new", "New Business"),
                            ("renewal", "Renewal"),
                            ("endorsement", "Endorsement"),
                            ("cancel", "Cancellation"),
                            ("reinstate", "Reinstatement"),
                        ],
                        help_text="Type of premium-affecting transaction",
                        max_length=20,
                        verbose_name="Transaction Type",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(
                        help_text="When this transaction takes effect (drives earned premium timing)",
                        verbose_name="Transaction Effective Date",
                    ),
                ),
                (
                    "accounting_date",
                    models.DateField(
                        help_text="When booked to ledger (written premium period)",
                        verbose_name="Accounting Date",
                    ),
                ),
                (
                    "gross_written_premium",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Premium amount for this transaction (before taxes)",
                        max_digits=15,
                        verbose_name="Gross Written Premium",
                    ),
                ),
                (
                    "tax_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="State premium tax amount (GWP × state tax rate)",
                        max_digits=15,
                        verbose_name="Tax Amount",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="transactions",
                        to="policies.policy",
                        verbose_name="Policy",
                    ),
                ),
            ],
            options={
                "verbose_name": "Policy Transaction",
                "verbose_name_plural": "Policy Transactions",
                "db_table": "policy_transactions",
                "ordering": ["-accounting_date", "-created_at"],
            },
        ),
        # Create StateAllocation table
        migrations.CreateModel(
            name="StateAllocation",
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
                    "state",
                    models.CharField(
                        choices=[
                            ("AL", "Alabama"),
                            ("AK", "Alaska"),
                            ("AZ", "Arizona"),
                            ("AR", "Arkansas"),
                            ("CA", "California"),
                            ("CO", "Colorado"),
                            ("CT", "Connecticut"),
                            ("DE", "Delaware"),
                            ("FL", "Florida"),
                            ("GA", "Georgia"),
                            ("HI", "Hawaii"),
                            ("ID", "Idaho"),
                            ("IL", "Illinois"),
                            ("IN", "Indiana"),
                            ("IA", "Iowa"),
                            ("KS", "Kansas"),
                            ("KY", "Kentucky"),
                            ("LA", "Louisiana"),
                            ("ME", "Maine"),
                            ("MD", "Maryland"),
                            ("MA", "Massachusetts"),
                            ("MI", "Michigan"),
                            ("MN", "Minnesota"),
                            ("MS", "Mississippi"),
                            ("MO", "Missouri"),
                            ("MT", "Montana"),
                            ("NE", "Nebraska"),
                            ("NV", "Nevada"),
                            ("NH", "New Hampshire"),
                            ("NJ", "New Jersey"),
                            ("NM", "New Mexico"),
                            ("NY", "New York"),
                            ("NC", "North Carolina"),
                            ("ND", "North Dakota"),
                            ("OH", "Ohio"),
                            ("OK", "Oklahoma"),
                            ("OR", "Oregon"),
                            ("PA", "Pennsylvania"),
                            ("RI", "Rhode Island"),
                            ("SC", "South Carolina"),
                            ("SD", "South Dakota"),
                            ("TN", "Tennessee"),
                            ("TX", "Texas"),
                            ("UT", "Utah"),
                            ("VT", "Vermont"),
                            ("VA", "Virginia"),
                            ("WA", "Washington"),
                            ("WV", "West Virginia"),
                            ("WI", "Wisconsin"),
                            ("WY", "Wyoming"),
                            ("DC", "District of Columbia"),
                            ("AS", "American Samoa"),
                            ("GU", "Guam"),
                            ("MP", "Northern Mariana Islands"),
                            ("PR", "Puerto Rico"),
                            ("VI", "Virgin Islands"),
                        ],
                        help_text="State where premium is allocated",
                        max_length=2,
                        verbose_name="State",
                    ),
                ),
                (
                    "allocation_method",
                    models.CharField(
                        choices=[
                            ("hq", "Headquarters"),
                            ("payroll", "Payroll"),
                            ("headcount", "Headcount"),
                            ("revenue", "Revenue"),
                        ],
                        default="hq",
                        help_text="Method used to determine allocation percentage",
                        max_length=20,
                        verbose_name="Allocation Method",
                    ),
                ),
                (
                    "allocation_percent",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Percentage of transaction allocated to this state (e.g., 100.00)",
                        max_digits=5,
                        verbose_name="Allocation Percent",
                    ),
                ),
                (
                    "allocated_premium",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Premium amount allocated to this state",
                        max_digits=15,
                        verbose_name="Allocated Premium",
                    ),
                ),
                (
                    "transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="state_allocations",
                        to="policies.policytransaction",
                        verbose_name="Policy Transaction",
                    ),
                ),
            ],
            options={
                "verbose_name": "State Allocation",
                "verbose_name_plural": "State Allocations",
                "db_table": "state_allocations",
                "ordering": ["state"],
                "unique_together": {("transaction", "state")},
            },
        ),
        # Backfill existing policies
        migrations.RunPython(backfill_transactions_and_allocations, reverse_backfill),
    ]
