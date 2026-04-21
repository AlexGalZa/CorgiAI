from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0042_add_kidnap_ransom_coverage_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralPartner",
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
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "name",
                    models.CharField(
                        help_text="Display name of the referral partner",
                        max_length=255,
                        verbose_name="Name",
                    ),
                ),
                (
                    "slug",
                    models.SlugField(
                        help_text="Unique identifier used in referral URLs (e.g. 'remax')",
                        max_length=100,
                        unique=True,
                        verbose_name="Slug",
                    ),
                ),
                (
                    "commission_rate",
                    models.DecimalField(
                        decimal_places=2,
                        default=8.0,
                        help_text="Commission percentage owed to this partner on billing premium",
                        max_digits=5,
                        verbose_name="Commission Rate (%)",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
            ],
            options={
                "verbose_name": "Referral Partner",
                "verbose_name_plural": "Referral Partners",
                "db_table": "referral_partners",
            },
        ),
        migrations.AddField(
            model_name="quote",
            name="referral_partner",
            field=models.ForeignKey(
                blank=True,
                help_text="Partner who referred this quote via referral link",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="quotes",
                to="quotes.referralpartner",
                verbose_name="Referral Partner",
            ),
        ),
    ]
