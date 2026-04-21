from django.utils import timezone

from api_keys.models import (
    ApiKey,
    ApiKeyInvite,
    generate_api_key,
    generate_invite_token,
)


# Naming convention used to mark read-only keys until a dedicated
# `scope` column lands on `ApiKey` (see TODO on `create_readonly_key`).
READONLY_NAME_PREFIX = "[readonly] "
READONLY_SCOPE = "read_only"


class ApiKeyService:
    @staticmethod
    def create_key(name: str, organization=None, created_by=None) -> tuple[ApiKey, str]:
        raw, prefix, key_hash = generate_api_key()
        api_key = ApiKey.objects.create(
            name=name,
            organization=organization,
            prefix=prefix,
            key_hash=key_hash,
            created_by=created_by,
        )
        return api_key, raw

    @staticmethod
    def create_readonly_key(
        name: str,
        organization=None,
        created_by=None,
    ) -> tuple[ApiKey, str]:
        """Issue an API key scoped to read-only access (H18).

        The key's ``name`` is prefixed with ``[readonly]`` so that middleware
        and the admin UI can identify it as a read-only key.

        TODO(H18-follow-up): ``ApiKey`` currently has no ``scope`` column.
        Once one is added (e.g. ``scope = CharField(choices=[('full', ...),
        ('read_only', ...)])``), replace this naming-convention marker with an
        explicit ``scope=READONLY_SCOPE`` value and update the request auth
        middleware to gate non-safe HTTP methods on that field.
        """
        readable = (
            name
            if name.startswith(READONLY_NAME_PREFIX)
            else f"{READONLY_NAME_PREFIX}{name}"
        )
        return ApiKeyService.create_key(
            name=readable,
            organization=organization,
            created_by=created_by,
        )

    @staticmethod
    def is_readonly_key(api_key: ApiKey) -> bool:
        """Return True if the given ApiKey was provisioned as read-only."""
        return bool(
            api_key and api_key.name and api_key.name.startswith(READONLY_NAME_PREFIX)
        )

    @staticmethod
    def create_invite(created_by=None) -> tuple[ApiKeyInvite, str]:
        token = generate_invite_token()
        invite = ApiKeyInvite.objects.create(
            token=token,
            created_by=created_by,
        )
        return invite, token

    @staticmethod
    def redeem_invite(
        token: str,
        first_name: str,
        last_name: str,
        org_name: str,
        email: str,
    ) -> tuple[bool, str, str | None]:
        try:
            invite = ApiKeyInvite.objects.get(token=token)
        except ApiKeyInvite.DoesNotExist:
            return False, "Invalid or expired invite", None

        if not invite.is_valid():
            return False, "Invalid or expired invite", None

        api_key, raw = ApiKeyService.create_key(
            name=f"{org_name} — {first_name} {last_name}",
        )

        invite.is_used = True
        invite.used_at = timezone.now()
        invite.partner_first_name = first_name
        invite.partner_last_name = last_name
        invite.partner_org_name = org_name
        invite.partner_email = email
        invite.api_key = api_key
        invite.save()

        return (
            True,
            "API key created. Store it securely — it will not be shown again.",
            raw,
        )
