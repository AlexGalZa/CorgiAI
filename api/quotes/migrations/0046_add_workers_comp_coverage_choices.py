from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0045_remove_commission_rate_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="underwriteroverride",
            name="coverage",
            field=models.CharField(
                choices=[
                    ("commercial-general-liability", "Commercial General Liability"),
                    ("media-liability", "Media Liability"),
                    ("directors-and-officers", "Directors & Officers"),
                    ("representations-warranties", "Representations & Warranties"),
                    ("technology-errors-and-omissions", "Technology E&O"),
                    ("cyber-liability", "Cyber Liability"),
                    ("fiduciary-liability", "Fiduciary Liability"),
                    ("hired-and-non-owned-auto", "Hired & Non-Owned Auto"),
                    (
                        "employment-practices-liability",
                        "Employment Practices Liability",
                    ),
                    ("custom-commercial-auto", "Commercial Auto"),
                    ("custom-crime", "Crime Insurance"),
                    ("custom-kidnap-ransom", "Kidnap & Ransom"),
                    ("custom-med-malpractice", "Medical Malpractice"),
                    ("custom-workers-comp", "Workers Compensation"),
                    ("claims_history", "Claims History Review"),
                    ("company", "Company Eligibility Review"),
                ],
                max_length=50,
                verbose_name="Coverage",
            ),
        ),
    ]
