"""Add logo_url, website, industry, phone, billing_email to Organization.
Add db_table and ordering to Organization, OrganizationMember, OrganizationInvite."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0004_backfill_personal_org_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="logo_url",
            field=models.URLField(
                blank=True,
                help_text="URL to the organization's logo image",
                max_length=500,
                null=True,
                verbose_name="Logo URL",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="website",
            field=models.URLField(
                blank=True,
                help_text="Organization's website URL",
                max_length=500,
                null=True,
                verbose_name="Website",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="industry",
            field=models.CharField(
                blank=True,
                help_text="Industry or sector the organization operates in",
                max_length=100,
                null=True,
                verbose_name="Industry",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="Organization's primary phone number",
                max_length=20,
                null=True,
                verbose_name="Phone",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="billing_email",
            field=models.EmailField(
                blank=True,
                help_text="Email address for billing communications",
                max_length=254,
                null=True,
                verbose_name="Billing Email",
            ),
        ),
        migrations.AlterModelTable(
            name="organization",
            table="organizations_organization",
        ),
        migrations.AlterModelTable(
            name="organizationmember",
            table="organizations_organizationmember",
        ),
        migrations.AlterModelTable(
            name="organizationinvite",
            table="organizations_organizationinvite",
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={
                "ordering": ["name"],
                "verbose_name": "Organization",
                "verbose_name_plural": "Organizations",
            },
        ),
        migrations.AlterModelOptions(
            name="organizationmember",
            options={
                "ordering": ["organization", "role"],
                "verbose_name": "Organization Member",
                "verbose_name_plural": "Organization Members",
            },
        ),
        migrations.AlterModelOptions(
            name="organizationinvite",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Organization Invite",
                "verbose_name_plural": "Organization Invites",
            },
        ),
    ]
