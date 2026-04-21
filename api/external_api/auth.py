import hashlib

from django.utils import timezone
from ninja.security import HttpBearer

from api_keys.constants import API_KEY_PREFIX_LENGTH
from api_keys.models import ApiKey


class ApiKeyAuth(HttpBearer):
    def authenticate(self, request, token: str):
        if len(token) < API_KEY_PREFIX_LENGTH:
            return None
        prefix = token[:API_KEY_PREFIX_LENGTH]
        key_hash = hashlib.sha256(token.encode()).hexdigest()
        try:
            api_key = ApiKey.objects.select_related("organization").get(
                prefix=prefix,
                key_hash=key_hash,
                is_active=True,
            )
            ApiKey.objects.filter(pk=api_key.pk).update(last_used_at=timezone.now())
            return api_key
        except ApiKey.DoesNotExist:
            return None
