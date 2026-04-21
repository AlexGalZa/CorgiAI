from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0046_add_workers_comp_coverage_choices"),
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
                    ("custom-bop", "Business Owners Policy"),
                    ("custom-umbrella", "Umbrella"),
                    ("custom-excess-liability", "Excess Liability"),
                    ("claims_history", "Claims History Review"),
                    ("company", "Company Eligibility Review"),
                ],
                max_length=50,
                verbose_name="Coverage",
            ),
        ),
        migrations.AlterField(
            model_name="customproduct",
            name="product_type",
            field=models.CharField(
                choices=[
                    ("custom-cgl", "Commercial General Liability (CGL)"),
                    ("custom-do", "Directors & Officers (D&O)"),
                    ("custom-eo", "Errors & Omissions (E&O)"),
                    ("custom-tech-eo", "Technology E&O"),
                    ("custom-cyber", "Cyber Liability"),
                    ("custom-epli", "Employment Practices Liability (EPLI)"),
                    ("custom-workers-comp", "Workers Compensation"),
                    ("custom-bop", "Business Owners Policy"),
                    ("custom-umbrella", "Umbrella"),
                    ("custom-excess-liability", "Excess Liability"),
                    ("custom-hnoa", "Hired & Non-Owned Auto (HNOA)"),
                    ("custom-crime", "Crime Insurance"),
                    ("custom-kidnap-ransom", "Kidnap & Ransom"),
                    ("custom-med-malpractice", "Medical Malpractice"),
                    ("custom-property", "Commercial Property"),
                    ("custom-surety", "Surety Bond"),
                    ("custom-fiduciary", "Fiduciary Liability"),
                    ("custom-media", "Media Liability"),
                    ("custom-commercial-auto", "Commercial Auto"),
                    ("custom-other", "Other"),
                ],
                max_length=50,
                verbose_name="Product Type",
            ),
        ),
    ]
