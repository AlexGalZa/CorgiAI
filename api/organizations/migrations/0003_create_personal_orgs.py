from django.db import migrations


def create_personal_orgs(apps, schema_editor):
    User = apps.get_model("users", "User")
    Organization = apps.get_model("organizations", "Organization")
    OrganizationMember = apps.get_model("organizations", "OrganizationMember")
    Quote = apps.get_model("quotes", "Quote")
    Claim = apps.get_model("claims", "Claim")
    CustomCertificate = apps.get_model("certificates", "CustomCertificate")
    UserDocument = apps.get_model("users", "UserDocument")

    for user in User.objects.all():
        org = Organization.objects.create(
            name="Personal",
            owner=user,
            is_personal=True,
        )
        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role="owner",
        )

        Quote.objects.filter(user=user, organization__isnull=True).update(
            organization=org
        )
        Claim.objects.filter(user=user, organization__isnull=True).update(
            organization=org
        )
        CustomCertificate.objects.filter(user=user, organization__isnull=True).update(
            organization=org
        )
        UserDocument.objects.filter(user=user, organization__isnull=True).update(
            organization=org
        )


def reverse_personal_orgs(apps, schema_editor):
    Organization = apps.get_model("organizations", "Organization")
    Organization.objects.filter(is_personal=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0002_organization_is_personal"),
        ("quotes", "0037_quote_organization"),
        ("claims", "0004_claim_organization"),
        ("certificates", "0002_customcertificate_organization"),
        ("users", "0007_userdocument_organization"),
    ]

    operations = [
        migrations.RunPython(create_personal_orgs, reverse_personal_orgs),
    ]
