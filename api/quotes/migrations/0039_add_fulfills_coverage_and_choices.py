from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0038_quote_organization_not_null"),
    ]

    operations = [
        migrations.AddField(
            model_name="customproduct",
            name="fulfills_coverage",
            field=models.CharField(
                blank=True,
                help_text="If set, this product fulfills the selected brokered coverage and auto-creates an underwriter override",
                max_length=50,
                null=True,
                verbose_name="Fulfills Brokered Coverage",
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
                    ("custom-umbrella", "Umbrella / Excess Liability"),
                    ("custom-hnoa", "Hired & Non-Owned Auto (HNOA)"),
                    ("custom-crime", "Crime Insurance"),
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
                    ("claims_history", "Claims History Review"),
                    ("company", "Company Eligibility Review"),
                ],
                max_length=50,
                verbose_name="Coverage",
            ),
        ),
    ]
