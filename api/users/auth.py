import jwt
from datetime import datetime, timezone
from typing import TypedDict, Optional
from django.conf import settings
from ninja.security import HttpBearer
from asgiref.sync import sync_to_async
from users.models import User
from organizations.models import Organization, OrganizationMember


class TokenPayload(TypedDict, total=False):
    user_id: int
    type: str
    exp: float
    iat: float
    impersonator_id: Optional[int]


class JWTAuth(HttpBearer):
    @staticmethod
    def create_access_token(user_id: int, impersonator_id: Optional[int] = None) -> str:
        # Impersonation tokens expire in 15 minutes for security
        if impersonator_id:
            lifetime = 15 * 60  # 15 minutes
        else:
            lifetime = settings.JWT_ACCESS_TOKEN_LIFETIME
        payload: TokenPayload = {
            "user_id": user_id,
            "type": "access",
            "exp": datetime.now(timezone.utc).timestamp() + lifetime,
            "iat": datetime.now(timezone.utc).timestamp(),
        }
        if impersonator_id:
            payload["impersonator_id"] = impersonator_id
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def create_2fa_token(user_id: int) -> str:
        """Short-lived token issued after password auth, before 2FA verification."""
        payload: TokenPayload = {
            "user_id": user_id,
            "type": "2fa",
            "exp": datetime.now(timezone.utc).timestamp() + 300,  # 5 minutes
            "iat": datetime.now(timezone.utc).timestamp(),
        }
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def create_refresh_token(
        user_id: int, impersonator_id: Optional[int] = None
    ) -> str:
        # Impersonation refresh tokens also get shorter lifetime (15 min)
        if impersonator_id:
            lifetime = 15 * 60  # 15 minutes
        else:
            lifetime = settings.JWT_REFRESH_TOKEN_LIFETIME
        payload: TokenPayload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.now(timezone.utc).timestamp() + lifetime,
            "iat": datetime.now(timezone.utc).timestamp(),
        }
        if impersonator_id:
            payload["impersonator_id"] = impersonator_id
        return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")

    @staticmethod
    def decode_token(token: str) -> TokenPayload | None:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def _set_org_context(user, request):
        org_header = request.headers.get("X-Organization-Id")
        if org_header:
            try:
                org_id = int(org_header)
                membership = OrganizationMember.objects.filter(
                    user=user, organization_id=org_id
                ).first()
                if membership:
                    user.active_organization_id = org_id
                    user.active_org_role = membership.role
            except (ValueError, TypeError):
                pass

        if not getattr(user, "active_organization_id", None):
            personal_org = Organization.objects.filter(
                owner=user, is_personal=True
            ).first()
            if personal_org:
                user.active_organization_id = personal_org.id
                user.active_org_role = "owner"

    def authenticate(self, request, token: str) -> User | None:
        payload = self.decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        try:
            user = User.objects.get(id=payload["user_id"], is_active=True)
            user.is_impersonated = bool(payload.get("impersonator_id"))
            user.impersonator_id = payload.get("impersonator_id")

            self._set_org_context(user, request)

            return user
        except User.DoesNotExist:
            return None


class AsyncJWTAuth(JWTAuth):
    async def authenticate(self, request, token: str) -> User | None:
        payload = self.decode_token(token)
        if not payload or payload.get("type") != "access":
            return None
        try:
            user = await sync_to_async(User.objects.get)(
                id=payload["user_id"], is_active=True
            )
            user.is_impersonated = bool(payload.get("impersonator_id"))
            user.impersonator_id = payload.get("impersonator_id")

            await sync_to_async(self._set_org_context)(user, request)

            return user
        except User.DoesNotExist:
            return None
