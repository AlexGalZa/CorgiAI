from ninja import Schema
from datetime import datetime
from typing import Optional
from decimal import Decimal

from pydantic import field_validator

from organizations.models import OrganizationMember


class RegisterRequest(Schema):
    email: str
    first_name: str
    last_name: str
    phone_number: str = ""
    company_name: str = ""
    invite_code: str | None = None
    referral_code: str | None = None


class UserSelfUpdateSchema(Schema):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    company_name: str | None = None
    notification_preferences: dict | None = None

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v):
        if v is not None and len(v) > 150:
            raise ValueError("first_name must be 150 characters or fewer")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v):
        if v is not None and len(v) > 150:
            raise ValueError("last_name must be 150 characters or fewer")
        return v

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, v):
        if v is not None and len(v) > 20:
            raise ValueError("phone_number must be 20 characters or fewer")
        return v

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v):
        if v is not None and len(v) > 255:
            raise ValueError("company_name must be 255 characters or fewer")
        return v


class ChangePasswordRequest(Schema):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v):
        if len(v) < 8:
            raise ValueError("new_password must be at least 8 characters")
        has_letter = any(c.isalpha() for c in v)
        has_digit = any(c.isdigit() for c in v)
        if not has_letter or not has_digit:
            raise ValueError("new_password must contain both letters and digits")
        return v


class RequestLoginCodeRequest(Schema):
    email: str
    channel: str = "auto"  # 'auto', 'email', or 'sms'


class VerifyLoginCodeRequest(Schema):
    email: str
    code: str


class OtpResponse(Schema):
    success: bool
    message: str


class RefreshRequest(Schema):
    refresh_token: str


class TokenResponse(Schema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserResponse(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    phone_number: str
    company_name: str
    role: str = "policyholder"
    is_staff: bool = False
    created_at: datetime
    is_impersonated: bool = False
    organizations: list[dict] = []
    notification_preferences: dict = {}

    @classmethod
    def from_user(cls, user) -> dict:
        memberships = (
            OrganizationMember.objects.filter(user=user)
            .select_related("organization")
            .order_by("-organization__is_personal", "organization__name")
        )
        organizations = [
            {
                "id": m.organization.id,
                "name": m.organization.name,
                "role": m.role,
                "is_personal": m.organization.is_personal,
            }
            for m in memberships
        ]

        return cls(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
            company_name=user.company_name,
            role=getattr(user, "role", "policyholder"),
            is_staff=user.is_staff,
            created_at=user.created_at,
            is_impersonated=getattr(user, "is_impersonated", False),
            organizations=organizations,
            notification_preferences=getattr(user, "notification_preferences", {}),
        ).dict()


class AuthResponse(Schema):
    user: UserResponse
    tokens: TokenResponse


class CreateSSOSessionRequest(Schema):
    redirect_uri: str


class SSOSessionResponse(Schema):
    sso_token: str
    redirect_uri: str


class ExchangeSSOTokenRequest(Schema):
    sso_token: str


class Verify2FARequest(Schema):
    two_factor_token: str
    code: str = ""
    method: str = "totp"  # 'totp' or 'passkey'


class ErrorResponse(Schema):
    detail: str


class UserQuoteResponse(Schema):
    id: int
    quote_number: str
    status: str
    coverages: list[str]
    quote_amount: Optional[Decimal] = None
    created_at: datetime


class UserDocumentResponse(Schema):
    id: int
    category: str
    title: str
    policy_numbers: list[str]
    effective_date: Optional[str] = None
    expiration_date: Optional[str] = None
    original_filename: str
    file_size: int
    created_at: datetime

    @classmethod
    def from_document(cls, doc) -> dict:
        return cls(
            id=doc.id,
            category=doc.category,
            title=doc.title,
            policy_numbers=doc.policy_numbers or [],
            effective_date=doc.effective_date.isoformat()
            if doc.effective_date
            else None,
            expiration_date=doc.expiration_date.isoformat()
            if doc.expiration_date
            else None,
            original_filename=doc.original_filename,
            file_size=doc.file_size,
            created_at=doc.created_at,
        ).dict()


class DocumentsByCategoryResponse(Schema):
    policies: list[UserDocumentResponse]
    certificates: list[UserDocumentResponse]
    endorsements: list[UserDocumentResponse]
    receipts: list[UserDocumentResponse]
    loss_runs: list[UserDocumentResponse]
