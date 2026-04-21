"""
Seed one account per admin role for quick login.
Run: python manage.py shell < seed_roles.py
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from users.models import User  # noqa: E402
from organizations.models import Organization, OrganizationMember  # noqa: E402

PASSWORD = "corgi123"

ACCOUNTS = [
    {
        "email": "admin@corgi.com",
        "first_name": "Admin",
        "last_name": "User",
        "role": "admin",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "ae@corgi.com",
        "first_name": "Account",
        "last_name": "Executive",
        "role": "ae",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "aeu@corgi.com",
        "first_name": "Senior",
        "last_name": "Underwriter",
        "role": "ae_underwriting",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "bdr@corgi.com",
        "first_name": "Business",
        "last_name": "Dev Rep",
        "role": "bdr",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "finance@corgi.com",
        "first_name": "Finance",
        "last_name": "Manager",
        "role": "finance",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "broker@corgi.com",
        "first_name": "Broker",
        "last_name": "Partner",
        "role": "broker",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "readonly@corgi.com",
        "first_name": "Read",
        "last_name": "Only",
        "role": "read_only",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "email": "123",
        "first_name": "Super",
        "last_name": "Admin",
        "role": "admin",
        "is_staff": True,
        "is_superuser": True,
    },
]


# H18: Models a read_only role may view. No create/update/delete on any of them.
# Uses Django's built-in `view_<model>` permission codename convention.
READ_ONLY_VIEW_PERMS = {
    ("policies", "policy"): ["view_policy"],
    ("policies", "policytransaction"): ["view_policytransaction"],
    ("policies", "payment"): ["view_payment"],
    # "Customer" is represented via Organization in this codebase.
    ("organizations", "organization"): ["view_organization"],
}


def _assign_read_only_permissions(user):
    """Attach the minimal view_* permissions for policy/customer/transaction/payment.

    Permissions are attached via a dedicated `read_only_api` group so the set stays
    auditable and revoking it is a single group-membership flip.
    """
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    group, _ = Group.objects.get_or_create(name="read_only_api")

    perms = []
    for (app_label, model), codenames in READ_ONLY_VIEW_PERMS.items():
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            continue
        for codename in codenames:
            try:
                perms.append(Permission.objects.get(content_type=ct, codename=codename))
            except Permission.DoesNotExist:
                continue
    group.permissions.set(perms)
    user.groups.add(group)


for acc in ACCOUNTS:
    email = acc.pop("email")
    u, created = User.objects.get_or_create(email=email, defaults=acc)
    if not created:
        for k, v in acc.items():
            setattr(u, k, v)
        u.save()
    u.set_password(PASSWORD)
    u.save()

    if u.role == "read_only":
        _assign_read_only_permissions(u)

    # Ensure personal org exists
    personal_org = Organization.objects.filter(owner=u, is_personal=True).first()
    if not personal_org:
        personal_org = Organization.objects.create(
            name=f"{u.first_name}'s Workspace",
            owner=u,
            is_personal=True,
        )
        OrganizationMember.objects.get_or_create(
            organization=personal_org,
            user=u,
            defaults={"role": "owner"},
        )

    print(f"{'Created' if created else 'Updated'}: {email} ({u.role})")

print(f"\nAll accounts use password: {PASSWORD}")
