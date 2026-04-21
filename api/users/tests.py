"""
Tests for the users module.

Covers registration, email login code request/verification,
JWT token refresh, user profile retrieval, and impersonation logging.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from users.models import User, EmailLoginCode, ImpersonationLog
from users.service import UserService
from users.auth import JWTAuth
from users.schemas import RegisterRequest
from common.exceptions import (
    ValidationError,
    AuthenticationError,
    NotFoundError,
    AccessDeniedError,
)
from tests.factories import create_test_user, create_test_staff_user


class UserModelTest(TestCase):
    """Tests for the User model."""

    def test_create_user(self):
        user = User.objects.create_user(
            email="model@test.com",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "model@test.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="super@test.com",
            password="testpass123",
            first_name="Super",
            last_name="Admin",
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_user_str_returns_email(self):
        user = create_test_user(email="str@test.com")
        self.assertEqual(str(user), "str@test.com")

    def test_get_full_name(self):
        user = create_test_user(
            email="name@test.com", first_name="John", last_name="Doe"
        )
        self.assertEqual(user.get_full_name(), "John Doe")

    def test_email_required(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", first_name="No", last_name="Email")


class RegistrationTest(TestCase):
    """Tests for user registration flow."""

    @patch("users.service.EmailService")
    def test_register_creates_user_and_personal_org(self, mock_email):
        data = RegisterRequest(
            email="register@test.com",
            first_name="New",
            last_name="User",
            phone_number="5551234567",
            company_name="My Company",
        )
        user, tokens = UserService.register(data)

        self.assertEqual(user.email, "register@test.com")
        self.assertEqual(user.first_name, "New")
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)

        # Should have created a personal org
        from organizations.models import OrganizationMember

        memberships = OrganizationMember.objects.filter(user=user)
        self.assertEqual(memberships.count(), 1)
        self.assertTrue(memberships.first().organization.is_personal)

    @patch("users.service.EmailService")
    def test_register_duplicate_email_raises_error(self, mock_email):
        create_test_user(email="dupe@test.com")
        data = RegisterRequest(
            email="dupe@test.com",
            first_name="Dupe",
            last_name="User",
            phone_number="555",
            company_name="",
        )
        with self.assertRaises(ValidationError):
            UserService.register(data)

    @patch("users.service.EmailService")
    def test_register_sends_login_code(self, mock_email):
        data = RegisterRequest(
            email="code@test.com",
            first_name="Code",
            last_name="Test",
            phone_number="555",
            company_name="",
        )
        UserService.register(data)

        # Should have created a login code
        codes = EmailLoginCode.objects.filter(user__email="code@test.com")
        self.assertEqual(codes.count(), 1)


class EmailLoginCodeTest(TestCase):
    """Tests for email login code request and verification."""

    @patch("users.service.EmailService")
    def test_request_login_code(self, mock_email):
        user = create_test_user(email="login@test.com")
        UserService.request_login_code("login@test.com")

        codes = EmailLoginCode.objects.filter(user=user)
        self.assertEqual(codes.count(), 1)
        self.assertEqual(len(codes.first().code), 6)

    def test_request_login_code_nonexistent_user_raises_error(self):
        with self.assertRaises(NotFoundError):
            UserService.request_login_code("nonexistent@test.com")

    @patch("users.service.EmailService")
    def test_verify_login_code_success(self, mock_email):
        user = create_test_user(email="verify@test.com")
        code = EmailLoginCode.objects.create(
            user=user,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        verified_user, tokens = UserService.verify_login_code(
            "verify@test.com", "123456"
        )
        self.assertEqual(verified_user.id, user.id)
        self.assertIn("access_token", tokens)

        code.refresh_from_db()
        self.assertTrue(code.is_used)

    def test_verify_login_code_wrong_code_raises_error(self):
        user = create_test_user(email="wrong@test.com")
        EmailLoginCode.objects.create(
            user=user,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        with self.assertRaises(AuthenticationError):
            UserService.verify_login_code("wrong@test.com", "654321")

    def test_verify_login_code_expired_raises_error(self):
        user = create_test_user(email="expired@test.com")
        EmailLoginCode.objects.create(
            user=user,
            code="123456",
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        with self.assertRaises(AuthenticationError):
            UserService.verify_login_code("expired@test.com", "123456")

    def test_email_login_code_model_is_valid(self):
        user = create_test_user(email="valid@test.com")
        code = EmailLoginCode.objects.create(
            user=user,
            code="999999",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        self.assertTrue(code.is_valid())

    def test_email_login_code_used_is_not_valid(self):
        user = create_test_user(email="used@test.com")
        code = EmailLoginCode.objects.create(
            user=user,
            code="999999",
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=True,
        )
        self.assertFalse(code.is_valid())

    def test_email_login_code_max_attempts_not_valid(self):
        user = create_test_user(email="attempts@test.com")
        code = EmailLoginCode.objects.create(
            user=user,
            code="999999",
            expires_at=timezone.now() + timedelta(minutes=10),
            attempts=5,
        )
        self.assertFalse(code.is_valid())


class JWTTokenTest(TestCase):
    """Tests for JWT token creation and refresh."""

    def test_create_tokens(self):
        user = create_test_user(email="jwt@test.com")
        tokens = UserService.create_tokens(user)
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)
        self.assertEqual(tokens["token_type"], "Bearer")

    def test_refresh_tokens(self):
        user = create_test_user(email="refresh@test.com")
        tokens = UserService.create_tokens(user)
        new_tokens = UserService.refresh_tokens(tokens["refresh_token"])
        self.assertIn("access_token", new_tokens)
        self.assertIn("refresh_token", new_tokens)

    def test_refresh_with_invalid_token_raises_error(self):
        with self.assertRaises(AuthenticationError):
            UserService.refresh_tokens("invalid.token.here")

    def test_tokens_include_impersonator_id(self):
        user = create_test_user(email="imp@test.com")
        tokens = UserService.create_tokens(user, impersonator_id=42)
        payload = JWTAuth.decode_token(tokens["access_token"])
        self.assertEqual(payload["impersonator_id"], 42)


class ImpersonationTest(TestCase):
    """Tests for impersonation logging."""

    def test_start_impersonation(self):
        admin = create_test_staff_user(email="admin@imp.com")
        target = create_test_user(email="target@imp.com")

        imp_user, tokens, log = UserService.start_impersonation(
            admin, target.id, ip_address="127.0.0.1", user_agent="TestBrowser"
        )

        self.assertEqual(imp_user.id, target.id)
        self.assertIn("access_token", tokens)
        self.assertEqual(log.admin_user, admin)
        self.assertEqual(log.impersonated_user, target)
        self.assertEqual(log.ip_address, "127.0.0.1")

    def test_non_staff_cannot_impersonate(self):
        user = create_test_user(email="nonstaffadm@imp.com")
        target = create_test_user(email="target2@imp.com")

        with self.assertRaises(AccessDeniedError):
            UserService.start_impersonation(user, target.id)

    def test_cannot_impersonate_staff(self):
        admin = create_test_staff_user(email="admin2@imp.com")
        other_staff = create_test_staff_user(email="staff2@imp.com")

        with self.assertRaises(AccessDeniedError):
            UserService.start_impersonation(admin, other_staff.id)

    def test_stop_impersonation(self):
        admin = create_test_staff_user(email="admin3@imp.com")
        target = create_test_user(email="target3@imp.com")

        _, _, log = UserService.start_impersonation(admin, target.id)
        self.assertIsNone(log.ended_at)

        returned_user, tokens = UserService.stop_impersonation(target, admin.id)

        self.assertEqual(returned_user.id, admin.id)
        log.refresh_from_db()
        self.assertIsNotNone(log.ended_at)

    def test_impersonation_log_str(self):
        admin = create_test_staff_user(email="admin4@imp.com")
        target = create_test_user(email="target4@imp.com")
        log = ImpersonationLog.objects.create(
            admin_user=admin,
            impersonated_user=target,
        )
        self.assertIn("admin4@imp.com", str(log))
        self.assertIn("target4@imp.com", str(log))


class UpdateProfileTest(TestCase):
    """Tests for PATCH /api/v1/users/me."""

    def setUp(self):
        self.user = create_test_user(email="patch@test.com")
        token = JWTAuth.create_access_token(self.user.id)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_patch_me_updates_fields(self):
        resp = self.client.patch(
            "/api/v1/users/me",
            data=json.dumps({"first_name": "Updated", "company_name": "NewCo"}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["first_name"], "Updated")
        self.assertEqual(body["data"]["company_name"], "NewCo")
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.company_name, "NewCo")

    def test_patch_me_updates_notification_preferences(self):
        prefs = {"email_quotes": True, "email_claims": False}
        resp = self.client.patch(
            "/api/v1/users/me",
            data=json.dumps({"notification_preferences": prefs}),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.notification_preferences, prefs)

    def test_patch_me_requires_auth(self):
        resp = self.client.patch(
            "/api/v1/users/me",
            data=json.dumps({"first_name": "NoAuth"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


class ChangePasswordTest(TestCase):
    """Tests for POST /api/v1/users/change-password."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="pwchange@test.com",
            password="OldPass1",
            first_name="Pass",
            last_name="Test",
        )
        token = JWTAuth.create_access_token(self.user.id)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_change_password_happy_path(self):
        resp = self.client.post(
            "/api/v1/users/change-password",
            data=json.dumps(
                {"current_password": "OldPass1", "new_password": "NewPass2"}
            ),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["message"], "Password updated")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass2"))

    def test_change_password_wrong_current_returns_401(self):
        resp = self.client.post(
            "/api/v1/users/change-password",
            data=json.dumps(
                {"current_password": "WrongPass9", "new_password": "NewPass2"}
            ),
            content_type="application/json",
            **self.auth,
        )
        self.assertEqual(resp.status_code, 401)
        body = resp.json()
        self.assertFalse(body["success"])
        self.assertIn("incorrect", body["message"])
