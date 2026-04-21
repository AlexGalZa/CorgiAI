"""Add renewal_status and auto_renew to Policy, payment fields to Payment,
and create PolicyRenewal model."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("policies", "0024_alter_policy_status"),
        ("quotes", "0050_add_referral_partner_notification_emails"),
    ]

    operations = [
        # Policy renewal fields
        migrations.AddField(
            model_name="policy",
            name="renewal_status",
            field=models.CharField(
                choices=[
                    ("not_due", "Not Due"),
                    ("offered", "Offered"),
                    ("renewed", "Renewed"),
                    ("non_renewed", "Non-Renewed"),
                ],
                db_index=True,
                default="not_due",
                help_text="Current renewal status of this policy",
                max_length=20,
                verbose_name="Renewal Status",
            ),
        ),
        migrations.AddField(
            model_name="policy",
            name="auto_renew",
            field=models.BooleanField(
                default=False,
                help_text="Whether this policy should be automatically renewed at expiration",
                verbose_name="Auto Renew",
            ),
        ),
        # Payment new fields
        migrations.AddField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                blank=True,
                help_text="Payment method used (card, ach, wire)",
                max_length=20,
                null=True,
                verbose_name="Payment Method",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="refund_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Amount refunded, if applicable",
                max_digits=15,
                null=True,
                verbose_name="Refund Amount",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="refund_reason",
            field=models.TextField(
                blank=True,
                help_text="Reason for the refund",
                null=True,
                verbose_name="Refund Reason",
            ),
        ),
        migrations.AddField(
            model_name="payment",
            name="refunded_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when the refund was processed",
                null=True,
                verbose_name="Refunded At",
            ),
        ),
        # PolicyRenewal model
        migrations.CreateModel(
            name="PolicyRenewal",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        help_text="Current status of the renewal offer",
                        max_length=10,
                        verbose_name="Status",
                    ),
                ),
                (
                    "offered_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the renewal offer was sent to the customer",
                        null=True,
                        verbose_name="Offered At",
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the renewal offer expires",
                        null=True,
                        verbose_name="Expires At",
                    ),
                ),
                (
                    "accepted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the customer accepted the renewal",
                        null=True,
                        verbose_name="Accepted At",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes about this renewal",
                        null=True,
                        verbose_name="Notes",
                    ),
                ),
                (
                    "policy",
                    models.ForeignKey(
                        help_text="The policy being renewed",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="renewals",
                        to="policies.policy",
                        verbose_name="Policy",
                    ),
                ),
                (
                    "new_quote",
                    models.ForeignKey(
                        blank=True,
                        help_text="The quote generated for the renewal offer",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="renewal_for",
                        to="quotes.quote",
                        verbose_name="New Quote",
                    ),
                ),
            ],
            options={
                "db_table": "policy_renewals",
                "verbose_name": "Policy Renewal",
                "verbose_name_plural": "Policy Renewals",
                "ordering": ["-created_at"],
            },
        ),
    ]
