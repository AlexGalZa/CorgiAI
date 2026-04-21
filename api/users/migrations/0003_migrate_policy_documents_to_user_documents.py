# Generated manually for data migration

from django.db import migrations


FILE_TYPE_TO_CATEGORY = {
    "certificate-of-insurance": "certificate",
    "cgl-policy": "policy",
    "tech-policy": "policy",
}

FILE_TYPE_TO_TITLE = {
    "certificate-of-insurance": "Certificate of Insurance",
    "cgl-policy": "CGL Policy",
    "tech-policy": "Tech Policy",
}


def migrate_policy_documents_to_user_documents(apps, schema_editor):
    """Copy existing PolicyDocument records to UserDocument."""
    PolicyDocument = apps.get_model("policies", "PolicyDocument")
    UserDocument = apps.get_model("users", "UserDocument")

    for policy_doc in PolicyDocument.objects.select_related(
        "policy__quote__user"
    ).all():
        policy = policy_doc.policy
        user = policy.quote.user

        category = FILE_TYPE_TO_CATEGORY.get(policy_doc.file_type, "policy")
        title = FILE_TYPE_TO_TITLE.get(
            policy_doc.file_type, policy_doc.original_filename
        )

        # Check if UserDocument already exists for this file
        if not UserDocument.objects.filter(
            user=user, s3_key=policy_doc.s3_key
        ).exists():
            UserDocument.objects.create(
                user=user,
                category=category,
                title=title,
                policy_number=policy.policy_number,
                effective_date=policy.effective_date,
                expiration_date=policy.expiration_date,
                file_type=policy_doc.file_type,
                original_filename=policy_doc.original_filename,
                file_size=policy_doc.file_size,
                mime_type=policy_doc.mime_type,
                s3_key=policy_doc.s3_key,
                s3_url=policy_doc.s3_url,
            )


def reverse_migration(apps, schema_editor):
    """Remove UserDocument records that were migrated from PolicyDocument."""
    UserDocument = apps.get_model("users", "UserDocument")
    PolicyDocument = apps.get_model("policies", "PolicyDocument")

    # Get all s3_keys from PolicyDocument
    policy_doc_keys = set(PolicyDocument.objects.values_list("s3_key", flat=True))

    # Delete UserDocuments that match these keys
    UserDocument.objects.filter(s3_key__in=policy_doc_keys).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_add_user_document"),
        ("policies", "0003_rename_purchase_to_policy"),
    ]

    operations = [
        migrations.RunPython(
            migrate_policy_documents_to_user_documents,
            reverse_migration,
        ),
    ]
