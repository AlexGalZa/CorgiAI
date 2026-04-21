from django.db import migrations, models


def backfill_claim_report_date(apps, schema_editor):
    Claim = apps.get_model("claims", "Claim")
    for claim in Claim.objects.filter(claim_report_date__isnull=True):
        claim.claim_report_date = claim.created_at.date()
        claim.save(update_fields=["claim_report_date"])


class Migration(migrations.Migration):
    dependencies = [
        ("claims", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="claim",
            name="claim_report_date",
            field=models.DateField(
                blank=True,
                null=True,
                verbose_name="Claim Report Date",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="loss_state",
            field=models.CharField(
                blank=True,
                choices=[
                    ("AL", "Alabama"),
                    ("AK", "Alaska"),
                    ("AZ", "Arizona"),
                    ("AR", "Arkansas"),
                    ("CA", "California"),
                    ("CO", "Colorado"),
                    ("CT", "Connecticut"),
                    ("DE", "Delaware"),
                    ("DC", "District of Columbia"),
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
                ],
                max_length=2,
                null=True,
                verbose_name="Loss State",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="paid_loss",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name="Paid Loss",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="paid_lae",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name="Paid LAE",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="case_reserve_loss",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name="Case Reserve Loss",
            ),
        ),
        migrations.AddField(
            model_name="claim",
            name="case_reserve_lae",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=15,
                null=True,
                verbose_name="Case Reserve LAE",
            ),
        ),
        migrations.RunPython(backfill_claim_report_date, migrations.RunPython.noop),
    ]
