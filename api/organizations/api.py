"""
Organization API endpoints for multi-tenancy management.

Provides organization CRUD, team member management (invites, roles,
removal), and the ability to join/leave organizations. All data in
the Corgi system is org-scoped, and these endpoints control that scoping.

Most endpoints require JWT authentication. The invite preview endpoint
is public (no auth required).
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router

from common.schemas import ApiResponseSchema
from organizations.schemas import (
    CreateOrganizationRequest,
    JoinOrganizationRequest,
    CreateInviteRequest,
    ResendInviteRequest,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from organizations.service import OrganizationService
from users.auth import JWTAuth

router = Router(tags=["Organizations"])


@router.get("/invite-preview", response={200: ApiResponseSchema})
def invite_preview(request: HttpRequest, code: str) -> tuple[int, dict[str, Any]]:
    """Preview invite details (org name) without authentication.

    Used by the frontend to show the organization name before the
    user decides to join.

    Args:
        request: HTTP request (no auth required).
        code: Invite code from the invite URL.

    Returns:
        200 with organization name and invite status.
    """
    data = OrganizationService.get_invite_preview(code)
    return 200, {
        "success": True,
        "message": "OK",
        "data": data,
    }


@router.get("/list", auth=JWTAuth(), response={200: ApiResponseSchema})
def list_my_organizations(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """List all organizations the authenticated user belongs to.

    Includes the user's role in each organization and whether it's
    a personal org.

    Returns:
        200 with a list of organization summaries.
    """
    orgs = OrganizationService.get_user_organizations(request.auth)
    return 200, {
        "success": True,
        "message": "OK",
        "data": orgs,
    }


@router.get("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def get_my_organization(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Get details of the active organization.

    Returns the organization info, its members, and pending invites.

    Returns:
        200 with organization details including members and invites.
    """
    details = OrganizationService.get_organization_details(request.auth)
    return 200, {
        "success": True,
        "message": "Organization retrieved successfully",
        "data": details,
    }


@router.patch("/me", auth=JWTAuth(), response={200: ApiResponseSchema})
def update_my_organization(
    request: HttpRequest, data: UpdateOrganizationRequest
) -> tuple[int, dict[str, Any]]:
    """Update the active organization's details.

    Only organization owners can update organization info.

    Args:
        request: HTTP request with JWT-authenticated user (must be owner).
        data: Fields to update (name, phone, billing_email, website).

    Returns:
        200 with updated organization details.
    """
    OrganizationService.update_organization(request.auth, data)
    details = OrganizationService.get_organization_details(request.auth)
    return 200, {
        "success": True,
        "message": "Organization updated successfully",
        "data": details,
    }


@router.post("/", auth=JWTAuth(), response={201: ApiResponseSchema})
def create_organization(
    request: HttpRequest, data: CreateOrganizationRequest
) -> tuple[int, dict[str, Any]]:
    """Create a new organization.

    The authenticated user becomes the owner of the new organization.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: Organization name.

    Returns:
        201 with the new organization details.
    """
    org = OrganizationService.create_organization(request.auth, data.name)
    details = OrganizationService.get_organization_details(request.auth, org_id=org.id)
    return 201, {
        "success": True,
        "message": "Organization created successfully",
        "data": details,
    }


@router.post("/join", auth=JWTAuth(), response={200: ApiResponseSchema})
def join_organization(
    request: HttpRequest, data: JoinOrganizationRequest
) -> tuple[int, dict[str, Any]]:
    """Join an organization using an invite code.

    The user is added as a member with the role specified by the invite.

    Args:
        request: HTTP request with JWT-authenticated user.
        data: Invite code.

    Returns:
        200 with the joined organization details.
    """
    member = OrganizationService.join_organization(request.auth, data.code)
    details = OrganizationService.get_organization_details(
        request.auth, org_id=member.organization_id
    )
    return 200, {
        "success": True,
        "message": "Joined organization successfully",
        "data": details,
    }


@router.post("/invites", auth=JWTAuth(), response={201: ApiResponseSchema})
def create_invite(
    request: HttpRequest, data: CreateInviteRequest
) -> tuple[int, dict[str, Any]]:
    """Create an invite link for the active organization.

    Only organization owners can create invites. Supports optional
    max uses, expiration, and email-targeted invites.

    Args:
        request: HTTP request with JWT-authenticated user (must be owner).
        data: Invite configuration (role, max_uses, expires_at, email).

    Returns:
        201 with the invite code and details.
    """
    invite = OrganizationService.create_invite(
        user=request.auth,
        default_role=data.default_role,
        max_uses=data.max_uses,
        expires_at=data.expires_at,
        email=data.email,
    )
    return 201, {
        "success": True,
        "message": "Invite created successfully",
        "data": {
            "id": invite.id,
            "code": invite.code,
            "default_role": invite.default_role,
            "max_uses": invite.max_uses,
            "use_count": invite.use_count,
            "expires_at": invite.expires_at.isoformat() if invite.expires_at else None,
            "created_at": invite.created_at.isoformat(),
        },
    }


@router.post(
    "/invites/{invite_id}/resend", auth=JWTAuth(), response={200: ApiResponseSchema}
)
def resend_invite(
    request: HttpRequest, invite_id: int, data: ResendInviteRequest
) -> tuple[int, dict[str, Any]]:
    """Resend an invite email to a specific address.

    Args:
        request: HTTP request with JWT-authenticated user.
        invite_id: Primary key of the invite to resend.
        data: Email address to send the invite to.

    Returns:
        200 confirmation.
    """
    OrganizationService.resend_invite(request.auth, invite_id, data.email)
    return 200, {
        "success": True,
        "message": "Invite email sent",
        "data": None,
    }


@router.delete(
    "/invites/{invite_id}", auth=JWTAuth(), response={200: ApiResponseSchema}
)
def revoke_invite(request: HttpRequest, invite_id: int) -> tuple[int, dict[str, Any]]:
    """Revoke an existing invite, making the code invalid.

    Args:
        request: HTTP request with JWT-authenticated user.
        invite_id: Primary key of the invite to revoke.

    Returns:
        200 confirmation.
    """
    OrganizationService.revoke_invite(request.auth, invite_id)
    return 200, {
        "success": True,
        "message": "Invite revoked successfully",
        "data": None,
    }


@router.patch("/members/{user_id}", auth=JWTAuth(), response={200: ApiResponseSchema})
def update_member_role(
    request: HttpRequest, user_id: int, data: UpdateMemberRoleRequest
) -> tuple[int, dict[str, Any]]:
    """Update a member's role in the active organization.

    Only organization owners can change roles.

    Args:
        request: HTTP request with JWT-authenticated user (must be owner).
        user_id: ID of the member to update.
        data: New role (editor or viewer).

    Returns:
        200 with updated organization details.
    """
    OrganizationService.update_member_role(request.auth, user_id, data.role)
    details = OrganizationService.get_organization_details(request.auth)
    return 200, {
        "success": True,
        "message": "Member role updated successfully",
        "data": details,
    }


@router.delete("/members/{user_id}", auth=JWTAuth(), response={200: ApiResponseSchema})
def remove_member(request: HttpRequest, user_id: int) -> tuple[int, dict[str, Any]]:
    """Remove a member from the active organization.

    Only organization owners can remove members.

    Args:
        request: HTTP request with JWT-authenticated user (must be owner).
        user_id: ID of the member to remove.

    Returns:
        200 with updated organization details.
    """
    OrganizationService.remove_member(request.auth, user_id)
    details = OrganizationService.get_organization_details(request.auth)
    return 200, {
        "success": True,
        "message": "Member removed successfully",
        "data": details,
    }


@router.post("/leave", auth=JWTAuth(), response={200: ApiResponseSchema})
def leave_organization(request: HttpRequest) -> tuple[int, dict[str, Any]]:
    """Leave the active organization.

    The user's membership is removed. Organization owners cannot leave
    their own organization (they must transfer ownership first).

    Returns:
        200 confirmation.
    """
    OrganizationService.leave_organization(request.auth)
    return 200, {
        "success": True,
        "message": "Left organization successfully",
        "data": None,
    }
