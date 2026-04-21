from django.db import migrations


def create_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    readonly_group, _ = Group.objects.get_or_create(name="corgi_readonly")
    full_access_group, _ = Group.objects.get_or_create(name="corgi_full_access")
    admin_group, _ = Group.objects.get_or_create(name="corgi_admin")

    # Collect all view permissions for read-only
    view_perms = Permission.objects.filter(codename__startswith="view_")
    readonly_group.permissions.set(view_perms)

    # Full access: all permissions except managing users (add/change/delete user)
    sensitive_codenames = {"add_user", "change_user", "delete_user"}
    full_access_perms = Permission.objects.exclude(codename__in=sensitive_codenames)
    full_access_group.permissions.set(full_access_perms)

    # Admin: all permissions
    all_perms = Permission.objects.all()
    admin_group.permissions.set(all_perms)


def delete_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(
        name__in=["corgi_readonly", "corgi_full_access", "corgi_admin"]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0009_add_email_login_code"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_groups, delete_groups),
    ]
