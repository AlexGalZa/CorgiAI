"""
Tests for the organizations module.

Covers org creation, personal org auto-creation, membership roles,
invite creation/validation/redemption, and org data isolation.
"""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from organizations.models import Organization, OrganizationMember, OrganizationInvite
from organizations.service import OrganizationService
from common.exceptions import ValidationError, AccessDeniedError
from tests.factories import (
    create_test_user,
    create_personal_org,
    setup_user_with_org,
)


class OrganizationModelTest(TestCase):
    """Tests for the Organization model."""

    def test_org_str_returns_name(self):
        user = create_test_user()
        org = Organization.objects.create(name="Acme Corp", owner=user)
        self.assertEqual(str(org), "Acme Corp")

    def test_personal_org_flag(self):
        user = create_test_user()
        org = create_personal_org(user)
        self.assertTrue(org.is_personal)


class PersonalOrgAutoCreationTest(TestCase):
    """Tests for personal org auto-creation on registration."""

    def test_create_personal_org(self):
        user = create_test_user(email="personal@test.com")
        org = OrganizationService.create_personal_org(user)

        self.assertTrue(org.is_personal)
        self.assertEqual(org.owner, user)
        member = OrganizationMember.objects.get(organization=org, user=user)
        self.assertEqual(member.role, "owner")

    def test_personal_org_uses_company_name(self):
        user = create_test_user(email="named@test.com", company_name="My Startup")
        org = OrganizationService.create_personal_org(user)
        self.assertEqual(org.name, "My Startup")

    def test_personal_org_fallback_name(self):
        user = create_test_user(email="noname@test.com", company_name="")
        org = OrganizationService.create_personal_org(user)
        self.assertEqual(org.name, "Personal")


class OrganizationCreationTest(TestCase):
    """Tests for OrganizationService.create_organization."""

    def test_create_organization(self):
        user = create_test_user(email="creator@test.com")
        org = OrganizationService.create_organization(user, "New Team Org")

        self.assertEqual(org.name, "New Team Org")
        self.assertEqual(org.owner, user)
        self.assertFalse(org.is_personal)
        member = OrganizationMember.objects.get(organization=org, user=user)
        self.assertEqual(member.role, "owner")


class OrganizationMembershipRolesTest(TestCase):
    """Tests for org membership roles (owner, editor, viewer)."""

    def test_owner_can_edit(self):
        user, org = setup_user_with_org()
        user.active_org_role = "owner"
        self.assertTrue(OrganizationService.can_edit(user))

    def test_editor_can_edit(self):
        user, org = setup_user_with_org()
        user.active_org_role = "editor"
        self.assertTrue(OrganizationService.can_edit(user))

    def test_viewer_cannot_edit(self):
        user, org = setup_user_with_org()
        user.active_org_role = "viewer"
        self.assertFalse(OrganizationService.can_edit(user))

    def test_owner_can_access_billing(self):
        user, org = setup_user_with_org()
        user.active_org_role = "owner"
        self.assertTrue(OrganizationService.can_access_billing(user))

    def test_viewer_cannot_access_billing(self):
        user, org = setup_user_with_org()
        user.active_org_role = "viewer"
        self.assertFalse(OrganizationService.can_access_billing(user))


class OrganizationInviteTest(TestCase):
    """Tests for invite creation, validation, and redemption."""

    @patch("organizations.service.EmailService")
    def test_create_invite(self, mock_email):
        user, org = setup_user_with_org()
        invite = OrganizationService.create_invite(user, default_role="editor")

        self.assertIsNotNone(invite.code)
        self.assertEqual(len(invite.code), 8)
        self.assertEqual(invite.organization_id, org.id)
        self.assertEqual(invite.default_role, "editor")

    def test_invite_code_generation_unique(self):
        code1 = OrganizationInvite.generate_code()
        code2 = OrganizationInvite.generate_code()
        self.assertNotEqual(code1, code2)

    def test_invite_is_valid(self):
        user, org = setup_user_with_org()
        invite = OrganizationInvite.objects.create(
            organization=org,
            code="TEST1234",
            created_by=user,
            default_role="viewer",
        )
        self.assertTrue(invite.is_valid())

    def test_invite_revoked_is_not_valid(self):
        user, org = setup_user_with_org()
        invite = OrganizationInvite.objects.create(
            organization=org,
            code="REVOKED1",
            created_by=user,
            default_role="viewer",
            is_revoked=True,
        )
        self.assertFalse(invite.is_valid())

    def test_invite_expired_is_not_valid(self):
        user, org = setup_user_with_org()
        invite = OrganizationInvite.objects.create(
            organization=org,
            code="EXPIRED1",
            created_by=user,
            default_role="viewer",
            expires_at=timezone.now() - timezone.timedelta(hours=1),
        )
        self.assertFalse(invite.is_valid())

    def test_invite_max_uses_exceeded_is_not_valid(self):
        user, org = setup_user_with_org()
        invite = OrganizationInvite.objects.create(
            organization=org,
            code="MAXUSED1",
            created_by=user,
            default_role="viewer",
            max_uses=1,
            use_count=1,
        )
        self.assertFalse(invite.is_valid())

    def test_join_organization_via_invite(self):
        owner, org = setup_user_with_org()
        invite = OrganizationInvite.objects.create(
            organization=org,
            code="JOIN1234",
            created_by=owner,
            default_role="editor",
        )

        new_user = create_test_user(email="newmember@test.com")
        new_user.active_organization_id = None
        new_user.active_org_role = None

        member = OrganizationService.join_organization(new_user, "JOIN1234")
        self.assertEqual(member.organization, org)
        self.assertEqual(member.role, "editor")

        invite.refresh_from_db()
        self.assertEqual(invite.use_count, 1)

    def test_join_organization_invalid_code_raises_error(self):
        user = create_test_user(email="invalid@test.com")
        with self.assertRaises(ValidationError):
            OrganizationService.join_organization(user, "BADCODE1")

    def test_join_organization_already_member_raises_error(self):
        owner, org = setup_user_with_org()
        OrganizationInvite.objects.create(
            organization=org,
            code="DUPL1234",
            created_by=owner,
            default_role="viewer",
        )
        with self.assertRaises(ValidationError):
            OrganizationService.join_organization(owner, "DUPL1234")


class OrganizationMemberManagementTest(TestCase):
    """Tests for member management (remove, role update)."""

    def test_remove_member(self):
        owner, org = setup_user_with_org()
        member_user = create_test_user(email="member@test.com")
        OrganizationMember.objects.create(
            organization=org, user=member_user, role="editor"
        )

        OrganizationService.remove_member(owner, member_user.id)
        self.assertFalse(
            OrganizationMember.objects.filter(
                organization=org, user=member_user
            ).exists()
        )

    def test_owner_cannot_remove_self(self):
        owner, org = setup_user_with_org()
        with self.assertRaises(ValidationError):
            OrganizationService.remove_member(owner, owner.id)

    def test_non_owner_cannot_remove_members(self):
        owner, org = setup_user_with_org()
        editor = create_test_user(email="editor@test.com")
        OrganizationMember.objects.create(organization=org, user=editor, role="editor")
        editor.active_organization_id = org.id
        editor.active_org_role = "editor"

        viewer = create_test_user(email="viewer@test.com")
        OrganizationMember.objects.create(organization=org, user=viewer, role="viewer")

        with self.assertRaises(AccessDeniedError):
            OrganizationService.remove_member(editor, viewer.id)

    def test_update_member_role(self):
        owner, org = setup_user_with_org()
        member_user = create_test_user(email="torole@test.com")
        OrganizationMember.objects.create(
            organization=org, user=member_user, role="viewer"
        )

        updated = OrganizationService.update_member_role(
            owner, member_user.id, "editor"
        )
        self.assertEqual(updated.role, "editor")


class OrganizationDataIsolationTest(TestCase):
    """Tests for org data isolation — users in org A can't see org B data."""

    def test_get_user_organizations_only_returns_own_orgs(self):
        user1 = create_test_user(email="user1@iso.com")
        user2 = create_test_user(email="user2@iso.com")
        org1 = create_personal_org(user1)
        org2 = create_personal_org(user2)

        user1_orgs = OrganizationService.get_user_organizations(user1)
        user2_orgs = OrganizationService.get_user_organizations(user2)

        user1_org_ids = {o["id"] for o in user1_orgs}
        user2_org_ids = {o["id"] for o in user2_orgs}

        self.assertIn(org1.id, user1_org_ids)
        self.assertNotIn(org2.id, user1_org_ids)
        self.assertIn(org2.id, user2_org_ids)
        self.assertNotIn(org1.id, user2_org_ids)


class OrganizationLeaveTest(TestCase):
    """Tests for leaving an organization."""

    def test_leave_organization(self):
        owner, org = setup_user_with_org()
        # Service refuses to let anyone leave a personal org; flip the
        # flag so we're testing the leave path, not the personal-org guard.
        org.is_personal = False
        org.save()
        member = create_test_user(email="leaver@test.com")
        OrganizationMember.objects.create(organization=org, user=member, role="editor")
        member.active_organization_id = org.id
        member.active_org_role = "editor"

        OrganizationService.leave_organization(member)
        self.assertFalse(
            OrganizationMember.objects.filter(organization=org, user=member).exists()
        )

    def test_owner_cannot_leave_org(self):
        owner, org = setup_user_with_org()
        # Make it non-personal
        org.is_personal = False
        org.save()

        with self.assertRaises(ValidationError):
            OrganizationService.leave_organization(owner)

    def test_cannot_leave_personal_org(self):
        user, org = setup_user_with_org()
        # Personal orgs can't be left
        with self.assertRaises(ValidationError):
            OrganizationService.leave_organization(user)
