"""
Smoke tests for self-serve policy endpoints landed this session:

    * POST /policies/{id}/reinstate          (V3 #6.5)
    * POST /policies/{id}/raise-limit        (V3 #6.4)
    * POST /policies/{id}/cancel             (V3 #5.1)

Each endpoint is exercised for a happy-path case and its org-scoping guard
(another organization's user must get a 404). Stripe SDK calls are mocked
via ``stripe_integration.service.StripeService.get_client`` — no network.
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase

from tests.factories import (
    create_personal_org,
    create_test_policy,
    create_test_quote,
    create_test_user,
    setup_user_with_org,
)
from users.auth import JWTAuth


def _auth_header(user):
    token = JWTAuth.create_access_token(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _attach_org_to_user(user, org):
    # active_organization_id / active_org_role aren't persisted columns on
    # the User model; they're in-memory request-state only. Create the
    # OrganizationMember record so middleware + permission checks pass, then
    # decorate the in-memory user so test assertions that read those
    # attributes keep working.
    from organizations.models import OrganizationMember

    OrganizationMember.objects.get_or_create(
        organization=org, user=user, defaults={"role": "owner"}
    )
    user.active_organization_id = org.id
    user.active_org_role = "owner"


class _StripeStub:
    """Minimal duck-typed stand-in for the stripe module returned by get_client()."""

    def __init__(self, sub_status="active"):
        self.Subscription = MagicMock()
        self.Subscription.retrieve.return_value = {"status": sub_status}
        self.Subscription.modify.return_value = {"status": sub_status}
        self.Subscription.resume.return_value = {"status": "active"}


# ════════════════════════════════════════════════════════════════════
# Reinstate (6.5)
# ════════════════════════════════════════════════════════════════════


class ReinstatePolicyEndpointTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.org = setup_user_with_org()
        quote = create_test_quote(user=self.user, org=self.org, status="purchased")
        self.policy = create_test_policy(
            quote=quote,
            status="cancelled",
            stripe_subscription_id="sub_test_reinstate",
        )

    @patch("stripe_integration.service.StripeService.get_client")
    def test_reinstate_happy_path_clears_scheduled_cancellation(self, mock_client):
        stub = _StripeStub(sub_status="active")
        mock_client.return_value = stub

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "active")

        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, "active")
        stub.Subscription.modify.assert_called_once()

    @patch("stripe_integration.service.StripeService.get_client")
    def test_reinstate_resumes_paused_subscription(self, mock_client):
        stub = _StripeStub(sub_status="paused")
        mock_client.return_value = stub

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 200)
        stub.Subscription.resume.assert_called_once_with("sub_test_reinstate")

    @patch("stripe_integration.service.StripeService.get_client")
    def test_reinstate_rejects_fully_cancelled_subscription(self, mock_client):
        stub = _StripeStub(sub_status="canceled")
        mock_client.return_value = stub

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)
        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, "cancelled")

    def test_reinstate_rejects_policy_from_different_org(self):
        """Org-scoping guard — another user gets a 404, never a 403."""
        other_user = create_test_user(email="other@example.com")
        other_org = create_personal_org(other_user)
        _attach_org_to_user(other_user, other_org)

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
            **_auth_header(other_user),
        )

        self.assertEqual(resp.status_code, 404)

    def test_reinstate_requires_auth(self):
        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)

    def test_reinstate_already_active_is_a_no_op(self):
        self.policy.status = "active"
        self.policy.save(update_fields=["status"])

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/reinstate",
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("already active", body["message"].lower())


# ════════════════════════════════════════════════════════════════════
# Raise Limit (6.4)
# ════════════════════════════════════════════════════════════════════


class RaiseLimitEndpointTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.org = setup_user_with_org()
        quote = create_test_quote(user=self.user, org=self.org, status="purchased")
        self.policy = create_test_policy(
            quote=quote,
            coverage_type="cyber-liability",
            status="active",
            premium=Decimal("1000.00"),
            limits_retentions={
                "aggregate_limit": 1_000_000,
                "per_occurrence_limit": 1_000_000,
                "retention": 10_000,
            },
        )

    @patch("policies.service.PolicyService.endorse_modify_limits")
    @patch("rating.service.RatingService._get_limit_factor")
    @patch("rating.rules.get_definition")
    def test_raise_limit_happy_path(self, mock_def, mock_factor, mock_endorse):
        mock_def.return_value = object()  # truthy — definition found
        # old=1.0, new=1.5 → ratio 1.5
        mock_factor.side_effect = [1.0, 1.5]
        mock_endorse.return_value = {"ok": True}

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/raise-limit",
            data=json.dumps({"coverage": "cyber-liability", "new_limit": 2_000_000}),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["new_limit"], 2_000_000)
        # Premium scaled by 1.5x
        self.assertEqual(body["data"]["new_premium"], "1500.00")
        mock_endorse.assert_called_once()

    @patch("rating.service.RatingService._get_limit_factor")
    @patch("rating.rules.get_definition")
    def test_raise_limit_rejects_decrease(self, mock_def, mock_factor):
        mock_def.return_value = object()
        mock_factor.side_effect = [1.0, 1.0]

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/raise-limit",
            data=json.dumps({"coverage": "cyber-liability", "new_limit": 500_000}),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("greater than", body["message"])

    def test_raise_limit_rejects_coverage_mismatch(self):
        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/raise-limit",
            data=json.dumps(
                {"coverage": "directors-and-officers", "new_limit": 2_000_000}
            ),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)
        body = resp.json()
        self.assertIn("Coverage mismatch", body["message"])

    def test_raise_limit_other_org_user_gets_404(self):
        other_user = create_test_user(email="other-raise@example.com")
        other_org = create_personal_org(other_user)
        _attach_org_to_user(other_user, other_org)

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/raise-limit",
            data=json.dumps({"coverage": "cyber-liability", "new_limit": 2_000_000}),
            content_type="application/json",
            **_auth_header(other_user),
        )

        self.assertEqual(resp.status_code, 404)

    def test_raise_limit_requires_auth(self):
        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/raise-limit",
            data=json.dumps({"coverage": "cyber-liability", "new_limit": 2_000_000}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)


# ════════════════════════════════════════════════════════════════════
# Cancel (5.1)
# ════════════════════════════════════════════════════════════════════


class CancelPolicyEndpointTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user, self.org = setup_user_with_org()
        quote = create_test_quote(user=self.user, org=self.org, status="purchased")
        self.policy = create_test_policy(
            quote=quote,
            status="active",
            stripe_subscription_id="sub_test_cancel",
            effective_date=date.today() - timedelta(days=30),
            expiration_date=date.today() + timedelta(days=335),
        )

    @patch("emails.service.EmailService.send")
    @patch("stripe_integration.service.StripeService.get_client")
    def test_cancel_happy_path_sets_pending_cancellation(self, mock_client, mock_email):
        stub = _StripeStub()
        mock_client.return_value = stub

        effective = (date.today() + timedelta(days=7)).isoformat()
        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": effective,
                    "reason": "too_expensive",
                    "reason_text": "Found a better rate",
                }
            ),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "pending_cancellation")

        self.policy.refresh_from_db()
        self.assertEqual(self.policy.status, "pending_cancellation")
        stub.Subscription.modify.assert_called_once()

    @patch("emails.service.EmailService.send")
    @patch("stripe_integration.service.StripeService.get_client")
    def test_cancel_rejects_past_effective_date(self, mock_client, mock_email):
        mock_client.return_value = _StripeStub()
        past = (date.today() - timedelta(days=1)).isoformat()

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": past,
                    "reason": "too_expensive",
                }
            ),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("past", resp.json()["message"].lower())

    @patch("emails.service.EmailService.send")
    @patch("stripe_integration.service.StripeService.get_client")
    def test_cancel_rejects_invalid_date_format(self, mock_client, mock_email):
        mock_client.return_value = _StripeStub()

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": "not-a-date",
                    "reason": "too_expensive",
                }
            ),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)

    def test_cancel_rejects_already_cancelled_policy(self):
        self.policy.status = "cancelled"
        self.policy.save(update_fields=["status"])

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": (date.today() + timedelta(days=1)).isoformat(),
                    "reason": "too_expensive",
                }
            ),
            content_type="application/json",
            **_auth_header(self.user),
        )

        self.assertEqual(resp.status_code, 400)

    def test_cancel_other_org_user_gets_404(self):
        other_user = create_test_user(email="other-cancel@example.com")
        other_org = create_personal_org(other_user)
        _attach_org_to_user(other_user, other_org)

        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": (date.today() + timedelta(days=5)).isoformat(),
                    "reason": "too_expensive",
                }
            ),
            content_type="application/json",
            **_auth_header(other_user),
        )

        self.assertEqual(resp.status_code, 404)

    def test_cancel_requires_auth(self):
        resp = self.client.post(
            f"/api/v1/policies/{self.policy.pk}/cancel",
            data=json.dumps(
                {
                    "effective_date": (date.today() + timedelta(days=5)).isoformat(),
                    "reason": "too_expensive",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)
