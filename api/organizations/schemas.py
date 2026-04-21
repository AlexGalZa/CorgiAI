from ninja import Schema
from typing import Optional
from datetime import datetime


class CreateOrganizationRequest(Schema):
    name: str


class JoinOrganizationRequest(Schema):
    code: str


class CreateInviteRequest(Schema):
    default_role: str = "viewer"
    max_uses: Optional[int] = None
    expires_at: Optional[datetime] = None
    email: Optional[str] = None


class UpdateOrganizationRequest(Schema):
    name: Optional[str] = None
    phone: Optional[str] = None
    billing_email: Optional[str] = None
    website: Optional[str] = None


class UpdateMemberRoleRequest(Schema):
    role: str


class ResendInviteRequest(Schema):
    email: str


class OrganizationMemberResponse(Schema):
    id: int
    email: str
    first_name: str
    last_name: str
    role: str
    joined_at: str

    @staticmethod
    def from_membership(m) -> "OrganizationMemberResponse":
        return OrganizationMemberResponse(
            id=m.user.id,
            email=m.user.email,
            first_name=m.user.first_name,
            last_name=m.user.last_name,
            role=m.role,
            joined_at=m.created_at.isoformat(),
        )


class OrganizationInviteResponse(Schema):
    id: int
    code: str
    default_role: str
    max_uses: Optional[int]
    use_count: int
    expires_at: Optional[str]
    is_valid: bool
    created_at: str

    @staticmethod
    def from_invite(inv) -> "OrganizationInviteResponse":
        return OrganizationInviteResponse(
            id=inv.id,
            code=inv.code,
            default_role=inv.default_role,
            max_uses=inv.max_uses,
            use_count=inv.use_count,
            expires_at=inv.expires_at.isoformat() if inv.expires_at else None,
            is_valid=inv.is_valid(),
            created_at=inv.created_at.isoformat(),
        )


class OrganizationDetailResponse(Schema):
    id: int
    name: str
    role: str
    is_personal: bool
    phone: Optional[str] = None
    billing_email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    members: list[OrganizationMemberResponse]
    invites: list[OrganizationInviteResponse]

    @staticmethod
    def from_org(
        org, membership, members_qs, invites_qs
    ) -> "OrganizationDetailResponse":
        return OrganizationDetailResponse(
            id=org.id,
            name=org.name,
            role=membership.role,
            is_personal=org.is_personal,
            phone=org.phone,
            billing_email=org.billing_email,
            website=org.website,
            industry=org.industry,
            members=[OrganizationMemberResponse.from_membership(m) for m in members_qs],
            invites=[OrganizationInviteResponse.from_invite(inv) for inv in invites_qs],
        )
