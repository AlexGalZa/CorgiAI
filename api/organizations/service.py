from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string

from common.exceptions import ValidationError, AccessDeniedError, NotFoundError
from emails.schemas import SendEmailInput
from emails.service import EmailService
from organizations.models import Organization, OrganizationMember, OrganizationInvite
from organizations.schemas import OrganizationDetailResponse
from users.models import User


class OrganizationService:
    @staticmethod
    def get_active_org_id(user) -> int:
        return user.active_organization_id

    @staticmethod
    def can_edit(user) -> bool:
        role = getattr(user, "active_org_role", None)
        return role in ("owner", "editor")

    @staticmethod
    def can_access_billing(user) -> bool:
        role = getattr(user, "active_org_role", None)
        return role in ("owner", "editor")

    @staticmethod
    def get_user_organizations(user) -> list[dict]:
        memberships = (
            OrganizationMember.objects.filter(user=user)
            .select_related("organization")
            .order_by("-organization__is_personal", "organization__name")
        )
        return [
            {
                "id": m.organization.id,
                "name": m.organization.name,
                "role": m.role,
                "is_personal": m.organization.is_personal,
            }
            for m in memberships
        ]

    @staticmethod
    def create_personal_org(user) -> Organization:
        # Company name if provided, otherwise literal "Personal". Tests lock
        # this in; personal orgs stay identifiable by is_personal=True.
        name = (
            user.company_name.strip()
            if user.company_name and user.company_name.strip()
            else "Personal"
        )
        org = Organization.objects.create(name=name, owner=user, is_personal=True)
        OrganizationMember.objects.create(organization=org, user=user, role="owner")
        return org

    @staticmethod
    def get_user_membership(user: User) -> OrganizationMember | None:
        return (
            OrganizationMember.objects.filter(user=user)
            .select_related("organization")
            .first()
        )

    @staticmethod
    @transaction.atomic
    def create_organization(user: User, name: str) -> Organization:
        org = Organization.objects.create(name=name, owner=user)
        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role="owner",
        )
        return org

    @staticmethod
    def update_organization(user: User, data) -> Organization:
        """Update organization details. Only owners can update."""
        org_id = OrganizationService.get_active_org_id(user)
        membership = OrganizationMember.objects.filter(
            user=user, organization_id=org_id
        ).first()
        if not membership or membership.role != "owner":
            raise AccessDeniedError(
                "Only the organization owner can update organization details"
            )

        org = Organization.objects.get(id=org_id)
        update_fields = []
        if data.name is not None:
            org.name = data.name
            update_fields.append("name")
        if data.phone is not None:
            org.phone = data.phone
            update_fields.append("phone")
        if data.billing_email is not None:
            org.billing_email = data.billing_email
            update_fields.append("billing_email")
        if data.website is not None:
            org.website = data.website
            update_fields.append("website")
        if update_fields:
            org.save(update_fields=update_fields)
        return org

    @staticmethod
    def create_invite(
        user: User,
        default_role: str = "viewer",
        max_uses: int | None = None,
        expires_at=None,
        email: str | None = None,
    ) -> OrganizationInvite:
        org_id = OrganizationService.get_active_org_id(user)
        membership = (
            OrganizationMember.objects.filter(user=user, organization_id=org_id)
            .select_related("organization")
            .first()
        )
        if not membership or membership.role != "owner":
            raise AccessDeniedError("Only the organization owner can create invites")

        code = OrganizationInvite.generate_code()
        invite = OrganizationInvite.objects.create(
            organization_id=org_id,
            code=code,
            created_by=user,
            default_role=default_role,
            max_uses=max_uses,
            expires_at=expires_at,
        )

        if email:
            invite_url = f"{settings.FRONTEND_URL}/invite/{code}"
            html = render_to_string(
                "emails/org_invite.html",
                {
                    "inviter_name": user.first_name or user.email,
                    "org_name": membership.organization.name,
                    "invite_url": invite_url,
                },
            )
            try:
                EmailService.send(
                    SendEmailInput(
                        to=[email],
                        from_email=settings.HELLO_CORGI_EMAIL,
                        subject=f"{user.first_name or 'Someone'} invited you to join {membership.organization.name} on Corgi",
                        html=html,
                    )
                )
            except Exception:
                pass

        return invite

    @staticmethod
    @transaction.atomic
    def join_organization(user: User, code: str) -> OrganizationMember:
        try:
            invite = OrganizationInvite.objects.select_related("organization").get(
                code=code.upper()
            )
        except OrganizationInvite.DoesNotExist:
            raise ValidationError("Invalid invite code")

        if not invite.is_valid():
            raise ValidationError("This invite code is no longer valid")

        if OrganizationMember.objects.filter(
            user=user, organization=invite.organization
        ).exists():
            raise ValidationError("You are already a member of this organization")

        member = OrganizationMember.objects.create(
            organization=invite.organization,
            user=user,
            role=invite.default_role,
        )

        invite.use_count += 1
        invite.save(update_fields=["use_count"])

        return member

    @staticmethod
    def remove_member(requesting_user: User, member_user_id: int) -> None:
        org_id = OrganizationService.get_active_org_id(requesting_user)
        req_membership = OrganizationMember.objects.filter(
            user=requesting_user, organization_id=org_id
        ).first()
        if not req_membership or req_membership.role != "owner":
            raise AccessDeniedError("Only the organization owner can remove members")

        if requesting_user.id == member_user_id:
            raise ValidationError("Cannot remove yourself as the owner")

        try:
            target = OrganizationMember.objects.get(
                organization_id=org_id,
                user_id=member_user_id,
            )
        except OrganizationMember.DoesNotExist:
            raise NotFoundError("Member not found")

        target.delete()

    @staticmethod
    def update_member_role(
        requesting_user: User, member_user_id: int, new_role: str
    ) -> OrganizationMember:
        org_id = OrganizationService.get_active_org_id(requesting_user)
        req_membership = OrganizationMember.objects.filter(
            user=requesting_user, organization_id=org_id
        ).first()
        if not req_membership or req_membership.role != "owner":
            raise AccessDeniedError("Only the organization owner can change roles")

        if requesting_user.id == member_user_id:
            raise ValidationError("Cannot change your own role")

        if new_role not in ("editor", "viewer"):
            raise ValidationError("Invalid role")

        try:
            target = OrganizationMember.objects.get(
                organization_id=org_id,
                user_id=member_user_id,
            )
        except OrganizationMember.DoesNotExist:
            raise NotFoundError("Member not found")

        target.role = new_role
        target.save(update_fields=["role"])
        return target

    @staticmethod
    def resend_invite(user: User, invite_id: int, email: str) -> None:
        org_id = OrganizationService.get_active_org_id(user)
        membership = (
            OrganizationMember.objects.filter(user=user, organization_id=org_id)
            .select_related("organization")
            .first()
        )
        if not membership or membership.role != "owner":
            raise AccessDeniedError("Only the organization owner can send invites")

        try:
            invite = OrganizationInvite.objects.get(
                id=invite_id, organization_id=org_id
            )
        except OrganizationInvite.DoesNotExist:
            raise NotFoundError("Invite not found")

        if not invite.is_valid():
            raise ValidationError("This invite code is no longer valid")

        invite_url = f"{settings.FRONTEND_URL}/invite/{invite.code}"
        html = render_to_string(
            "emails/org_invite.html",
            {
                "inviter_name": user.first_name or user.email,
                "org_name": membership.organization.name,
                "invite_url": invite_url,
            },
        )
        EmailService.send(
            SendEmailInput(
                to=[email],
                from_email=settings.HELLO_CORGI_EMAIL,
                subject=f"{user.first_name or 'Someone'} invited you to join {membership.organization.name} on Corgi",
                html=html,
            )
        )

    @staticmethod
    def revoke_invite(user: User, invite_id: int) -> None:
        org_id = OrganizationService.get_active_org_id(user)
        membership = OrganizationMember.objects.filter(
            user=user, organization_id=org_id
        ).first()
        if not membership or membership.role != "owner":
            raise AccessDeniedError("Only the organization owner can revoke invites")

        try:
            invite = OrganizationInvite.objects.get(
                id=invite_id,
                organization_id=org_id,
            )
        except OrganizationInvite.DoesNotExist:
            raise NotFoundError("Invite not found")

        invite.is_revoked = True
        invite.save(update_fields=["is_revoked"])

    @staticmethod
    def validate_invite(code: str) -> OrganizationInvite:
        try:
            invite = OrganizationInvite.objects.select_related("organization").get(
                code=code.upper()
            )
        except OrganizationInvite.DoesNotExist:
            raise ValidationError("Invalid invite code")

        if not invite.is_valid():
            raise ValidationError("This invite code is no longer valid")

        return invite

    @staticmethod
    def get_invite_preview(code: str) -> dict:
        try:
            invite = OrganizationInvite.objects.select_related(
                "organization", "created_by"
            ).get(code=code.upper())
        except OrganizationInvite.DoesNotExist:
            raise ValidationError("Invalid invite code")

        if not invite.is_valid():
            raise ValidationError("This invite code is no longer valid")

        return {
            "org_name": invite.organization.name,
            "inviter_first_name": invite.created_by.first_name
            if invite.created_by
            else None,
            "default_role": invite.default_role,
        }

    @staticmethod
    def leave_organization(user: User) -> None:
        org_id = OrganizationService.get_active_org_id(user)
        org = Organization.objects.filter(id=org_id).first()
        if org and org.is_personal:
            raise ValidationError("Cannot leave your personal organization")

        membership = OrganizationMember.objects.filter(
            user=user, organization_id=org_id
        ).first()
        if not membership:
            raise ValidationError("You are not a member of this organization")

        if membership.role == "owner":
            raise ValidationError(
                "The owner cannot leave the organization. Transfer ownership first."
            )

        membership.delete()

    @staticmethod
    def get_organization_details(user: User, org_id: int = None) -> dict | None:
        target_org_id = org_id or OrganizationService.get_active_org_id(user)
        if not target_org_id:
            return None

        membership = (
            OrganizationMember.objects.filter(user=user, organization_id=target_org_id)
            .select_related("organization")
            .first()
        )
        if not membership:
            return None

        org = membership.organization
        members = OrganizationMember.objects.filter(organization=org).select_related(
            "user"
        )
        invites = OrganizationInvite.objects.filter(organization=org, is_revoked=False)

        return OrganizationDetailResponse.from_org(
            org, membership, members, invites
        ).dict()
