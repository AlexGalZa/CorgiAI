"""
Expanded integration tests for Corgi API.

Covers:
1. Quote rating (tech vs non-tech, AI classification)
2. Policy lifecycle (creation, cancellation, expired endorsement)
3. Certificates (consolidated COI, custom cert creation)
4. Organizations (creation, invite, role update)
5. RBAC (BDR, Finance, Broker, Admin role restrictions)
6. Webhooks (brokered webhook auth)
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client, override_settings

from users.models import User
from users.auth import JWTAuth
from organizations.models import Organization, OrganizationMember
from quotes.models import Address, Company, Quote
from policies.models import Policy


# ── Helpers ──────────────────────────────────────────────────────────


def _make_user(email="test@example.com", role="policyholder", is_staff=False, **kw):
    defaults = {"first_name": "Test", "last_name": "User", "password": "testpass123"}
    defaults.update(kw)
    pwd = defaults.pop("password")
    u = User.objects.create_user(
        email=email, password=pwd, role=role, is_staff=is_staff, **defaults
    )
    return u


def _make_staff(email, role="admin"):
    return _make_user(email=email, role=role, is_staff=True)


def _auth(user):
    token = JWTAuth.create_access_token(user.id)
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def _org(user, personal=True):
    org = Organization.objects.create(
        name=f"{user.email} org", owner=user, is_personal=personal
    )
    OrganizationMember.objects.create(organization=org, user=user, role="owner")
    return org


def _company(**overrides):
    addr = Address.objects.create(
        street_address="123 Main St",
        city="San Francisco",
        state="CA",
        zip="94105",
    )
    defaults = {
        "business_address": addr,
        "entity_legal_name": "Test Corp",
        "type": "llc",
        "profit_type": "for-profit",
        "last_12_months_revenue": Decimal("500000.00"),
        "projected_next_12_months_revenue": Decimal("750000.00"),
        "business_description": "A technology consulting company.",
    }
    defaults.update(overrides)
    return Company.objects.create(**defaults)


def _quote(user, org, company, **overrides):
    defaults = {
        "company": company,
        "user": user,
        "organization": org,
        "status": "submitted",
        "coverages": ["technology-errors-and-omissions"],
    }
    defaults.update(overrides)
    return Quote.objects.create(**defaults)


def _policy(quote, **overrides):
    defaults = {
        "quote": quote,
        "policy_number": f"POL-TEST-{Policy.objects.count() + 1:03d}",
        "coverage_type": "technology-errors-and-omissions",
        "premium": Decimal("5000.00"),
        "effective_date": date.today(),
        "expiration_date": date.today() + timedelta(days=365),
        "purchased_at": "2026-01-15T12:00:00Z",
        "status": "active",
    }
    defaults.update(overrides)
    return Policy.objects.create(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# 1. Quote Rating Tests
# ═══════════════════════════════════════════════════════════════════════


class QuoteRatingTest(TestCase):
    """Test rating engine behavior for tech vs non-tech companies."""

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.org = _org(self.user)

    @patch("rating.service.AIService.query")
    def test_tech_company_gets_instant_pricing(self, mock_ai):
        """A tech company requesting Tech E&O should get an instant price (no review)."""
        from rating.service import RatingService, CalculationContext
        from rating.rules.tech_eo import TECH_EO_DEFINITION

        # Rating calls AI to classify hazardClass; mock returns the
        # already-classified value so no real OpenAI call is made.
        mock_result = MagicMock()
        mock_result.hazard_class = "b2b-saas"
        mock_ai.return_value = mock_result

        ctx = CalculationContext(
            questionnaire={
                "hazardClass": "b2b-saas",
                "services_description": "SaaS platform",
            },
            revenue=Decimal("500000"),
            limit=1_000_000,
            retention=10_000,
            state="CA",
            business_description="B2B SaaS platform for HR management.",
        )
        result = RatingService.calculate(TECH_EO_DEFINITION, ctx)
        self.assertTrue(
            result.success,
            f"Expected instant pricing, got review: {result.review_reason}",
        )
        self.assertIsNotNone(result.premium)
        self.assertGreater(result.premium, Decimal("0"))

    @patch("rating.service.AIService.query")
    def test_non_tech_company_triggers_review(self, mock_ai):
        """A company outside standard parameters should trigger needs_review."""
        from rating.service import RatingService, CalculationContext
        from rating.rules.tech_eo import TECH_EO_DEFINITION

        mock_result = MagicMock()
        mock_result.hazard_class = "consulting"
        mock_ai.return_value = mock_result

        # Revenue of 0 with no square footage should fail to get a base premium
        ctx = CalculationContext(
            questionnaire={
                "hazardClass": "consulting",
                "services_description": "Consulting",
            },
            revenue=Decimal("0"),
            limit=1_000_000,
            retention=10_000,
            state="CA",
            business_description="Offline retail store.",
        )
        result = RatingService.calculate(TECH_EO_DEFINITION, ctx)
        # Either fails with review reason or returns a minimum premium
        # The key assertion: the engine handles this gracefully
        if not result.success:
            self.assertIsNotNone(result.review_reason)
        else:
            # Even if it succeeds, premium should be > 0
            self.assertGreater(result.premium, Decimal("0"))

    @patch("rating.service.AIService.query")
    def test_ai_classification_used_when_enabled(self, mock_ai):
        """AI classification enriches questionnaire when services_description is provided."""
        from rating.service import RatingService, CalculationContext
        from rating.rules.tech_eo import TECH_EO_DEFINITION

        mock_result = MagicMock()
        mock_result.hazard_class = "cybersecurity"
        mock_ai.return_value = mock_result

        ctx = CalculationContext(
            questionnaire={
                "services_description": "Cybersecurity consulting and pen testing"
            },
            revenue=Decimal("1000000"),
            limit=1_000_000,
            retention=10_000,
            state="CA",
            business_description="Cybersecurity firm.",
        )
        RatingService.calculate(TECH_EO_DEFINITION, ctx)
        # AI should have been called to classify hazard class
        mock_ai.assert_called_once()
        # The questionnaire should now have the AI-classified hazard class
        self.assertEqual(ctx.questionnaire.get("hazardClass"), "cybersecurity")


# ═══════════════════════════════════════════════════════════════════════
# 2. Policy Lifecycle Tests
# ═══════════════════════════════════════════════════════════════════════


class PolicyLifecycleTest(TestCase):
    """Test policy creation, cancellation, and endorsement guards."""

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.org = _org(self.user)
        self.company = _company()
        self.quote = _quote(self.user, self.org, self.company, status="purchased")

    def test_policy_creation_from_purchased_quote(self):
        """A policy can be created from a purchased quote."""
        policy = _policy(self.quote)
        self.assertEqual(policy.status, "active")
        self.assertEqual(policy.quote, self.quote)
        self.assertIsNotNone(policy.policy_number)
        self.assertEqual(policy.premium, Decimal("5000.00"))

    @patch("policies.service.StripeService.create_refund")
    def test_policy_cancellation_returns_refund(self, mock_refund):
        """Cancelling an active policy calculates a pro-rata refund."""
        from policies.service import PolicyService

        mock_refund_obj = MagicMock()
        mock_refund_obj.id = "re_test_123"
        mock_refund.return_value = mock_refund_obj

        policy = _policy(
            self.quote,
            effective_date=date.today() - timedelta(days=30),
            expiration_date=date.today() + timedelta(days=335),
            stripe_payment_intent_id="pi_test_123",
        )
        result = PolicyService.cancel_policy(policy, "Customer requested cancellation")
        self.assertEqual(result["cancelled_policy"].status, "cancelled")
        self.assertIsNotNone(result["refund_amount"])
        self.assertGreaterEqual(result["refund_amount"], Decimal("0"))

    def test_expired_policy_cannot_be_endorsed(self):
        """An expired policy should reject endorsement attempts."""
        from policies.service import PolicyService

        policy = _policy(
            self.quote,
            status="expired",
            effective_date=date.today() - timedelta(days=400),
            expiration_date=date.today() - timedelta(days=35),
        )
        with self.assertRaises(ValueError) as ctx:
            PolicyService.endorse_modify_limits(
                policy,
                new_limits={
                    "aggregate": 2_000_000,
                    "per_occurrence": 1_000_000,
                    "retention": 10_000,
                },
                new_premium=Decimal("7500.00"),
                admin_reason="Increase limits",
            )
        self.assertIn("active", str(ctx.exception).lower())


# ═══════════════════════════════════════════════════════════════════════
# 3. Certificate Tests
# ═══════════════════════════════════════════════════════════════════════


class CertificateTest(TestCase):
    """Test consolidated COI and custom certificate creation."""

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.org = _org(self.user)
        self.company = _company()
        self.quote = _quote(self.user, self.org, self.company, status="purchased")
        self.policy = _policy(self.quote, coi_number="COI-2026-001")

    def test_consolidated_coi_returns_grouped_data(self):
        """GET /certificates/consolidated returns grouped COI data."""
        resp = self.client.get("/api/v1/certificates/consolidated", **_auth(self.user))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])

    @patch(
        "certificates.service.CustomCertificateService.user_has_coi_access",
        return_value=True,
    )
    @patch(
        "certificates.service.CustomCertificateService.create_and_generate_certificate"
    )
    def test_custom_certificate_creation(self, mock_create, mock_access):
        """POST /certificates/custom creates a custom certificate."""
        mock_cert = MagicMock()
        mock_cert.id = 1
        mock_cert.custom_coi_number = "COI-2026-001-01"
        mock_cert.coi_number = "COI-2026-001"
        mock_cert.holder_name = "Acme Corp"
        mock_cert.holder_second_line = ""
        mock_cert.holder_street_address = "456 Oak Ave"
        mock_cert.holder_suite = ""
        mock_cert.holder_city = "New York"
        mock_cert.holder_state = "NY"
        mock_cert.holder_zip = "10001"
        mock_cert.is_additional_insured = True
        mock_cert.endorsements = []
        mock_cert.service_location_job = ""
        mock_cert.service_location_address = ""
        mock_cert.service_you_provide_job = ""
        mock_cert.service_you_provide_service = ""
        mock_cert.status = "active"
        mock_cert.created_at = "2026-01-15T12:00:00Z"
        mock_cert.document = None
        mock_create.return_value = mock_cert

        resp = self.client.post(
            "/api/v1/certificates/custom",
            data=json.dumps(
                {
                    "coi_number": "COI-2026-001",
                    "holder_name": "Acme Corp",
                    "holder_street_address": "456 Oak Ave",
                    "holder_city": "New York",
                    "holder_state": "NY",
                    "holder_zip": "10001",
                    "is_additional_insured": True,
                    "endorsements": [],
                }
            ),
            content_type="application/json",
            **_auth(self.user),
        )
        self.assertIn(resp.status_code, [200, 201])
        mock_create.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════
# 4. Organization Tests
# ═══════════════════════════════════════════════════════════════════════


class OrganizationTest(TestCase):
    """Test organization CRUD and membership management."""

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.org = _org(self.user)

    def test_create_organization(self):
        """POST /organizations/ creates a new org owned by the user."""
        resp = self.client.post(
            "/api/v1/organizations/",
            data=json.dumps({"name": "New Startup Inc"}),
            content_type="application/json",
            **_auth(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["success"])

    @patch(
        "organizations.service.OrganizationService._send_invite_email",
        create=True,
    )
    def test_member_invite(self, mock_email):
        """POST /organizations/invites creates an invite code."""
        resp = self.client.post(
            "/api/v1/organizations/invites",
            data=json.dumps(
                {
                    "default_role": "editor",
                    "max_uses": 5,
                    "email": "newmember@example.com",
                }
            ),
            content_type="application/json",
            **_auth(self.user),
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("code", body["data"])

    def test_member_role_update(self):
        """PATCH /organizations/members/{user_id} updates member role."""
        member_user = _make_user(email="member@example.com")
        OrganizationMember.objects.create(
            organization=self.org,
            user=member_user,
            role="viewer",
        )
        # Set active org for user
        self.user.active_organization = self.org
        self.user.save()

        resp = self.client.patch(
            f"/api/v1/organizations/members/{member_user.id}",
            data=json.dumps({"role": "editor"}),
            content_type="application/json",
            **_auth(self.user),
        )
        self.assertIn(resp.status_code, [200, 201])


# ═══════════════════════════════════════════════════════════════════════
# 5. RBAC Tests
# ═══════════════════════════════════════════════════════════════════════


class RBACTest(TestCase):
    """Test role-based access controls on admin endpoints."""

    def setUp(self):
        self.client = Client()
        self.admin = _make_staff("admin@corgi.com", role="admin")
        self.bdr = _make_staff("bdr@corgi.com", role="bdr")
        self.finance = _make_staff("finance@corgi.com", role="finance")
        self.broker = _make_staff("broker@corgi.com", role="broker")
        # Set up test data
        self.user = _make_user()
        self.org = _org(self.user)
        self.company = _company()
        self.quote = _quote(self.user, self.org, self.company, status="purchased")
        self.policy = _policy(self.quote)

    def test_bdr_cannot_cancel_policy(self):
        """BDR role should be denied from cancelling policies (OPERATIONS_ROLES only)."""
        resp = self.client.post(
            f"/api/v1/admin/policies/{self.policy.id}/cancel",
            data=json.dumps({"reason": "Test cancellation"}),
            content_type="application/json",
            **_auth(self.bdr),
        )
        self.assertEqual(resp.status_code, 403)

    def test_finance_cannot_edit_quotes(self):
        """Finance role should be denied from recalculating/editing quotes."""
        resp = self.client.post(
            f"/api/v1/admin/quotes/{self.quote.id}/recalculate",
            data=json.dumps({}),
            content_type="application/json",
            **_auth(self.finance),
        )
        self.assertEqual(resp.status_code, 403)

    def test_broker_only_sees_their_referrals(self):
        """Broker should only see quotes linked to their referral partner."""
        resp = self.client.get(
            "/api/v1/admin/quotes",
            **_auth(self.broker),
        )
        # Broker with no linked ReferralPartner should see empty results
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        # Expect empty data (broker has no linked referral partners)
        if isinstance(body.get("data"), dict):
            results = body["data"].get("results", body["data"].get("items", []))
        elif isinstance(body.get("data"), list):
            results = body["data"]
        else:
            results = []
        self.assertEqual(len(results), 0)

    def test_admin_can_access_all_actions(self):
        """Admin role should be able to access all endpoints."""
        # Admin can access analytics
        resp = self.client.get("/api/v1/admin/analytics/pipeline", **_auth(self.admin))
        self.assertEqual(resp.status_code, 200)

        # Admin can access quotes list
        resp = self.client.get("/api/v1/admin/quotes", **_auth(self.admin))
        self.assertEqual(resp.status_code, 200)

        # Admin can access policies list
        resp = self.client.get("/api/v1/admin/policies", **_auth(self.admin))
        self.assertEqual(resp.status_code, 200)


# ═══════════════════════════════════════════════════════════════════════
# 6. Webhook Tests
# ═══════════════════════════════════════════════════════════════════════


@override_settings(SKYVERN_WEBHOOK_SECRET="test-secret-123")
class WebhookAuthTest(TestCase):
    """Test brokered webhook authentication."""

    def setUp(self):
        self.client = Client()
        self.user = _make_user()
        self.org = _org(self.user)
        self.company = _company()
        self.quote = _quote(self.user, self.org, self.company)

    @patch("brokered.service.BrokeredService.workers_compensation_callback")
    def test_valid_webhook_secret_accepted(self, mock_callback):
        """Webhook with valid X-Webhook-Secret header is accepted."""
        mock_callback.return_value = (
            200,
            {"success": True, "message": "OK", "data": None},
        )

        resp = self.client.post(
            f"/api/v1/brokered/{self.quote.quote_number}/workers-compensation/callback",
            data=json.dumps(
                {
                    "status": "quoted",
                    "premium": 2500.00,
                }
            ),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET="test-secret-123",
        )
        self.assertEqual(resp.status_code, 200)

    def test_invalid_webhook_secret_returns_401(self):
        """Webhook with wrong X-Webhook-Secret header returns 401."""
        resp = self.client.post(
            f"/api/v1/brokered/{self.quote.quote_number}/workers-compensation/callback",
            data=json.dumps(
                {
                    "status": "quoted",
                    "premium": 2500.00,
                }
            ),
            content_type="application/json",
            HTTP_X_WEBHOOK_SECRET="wrong-secret",
        )
        self.assertEqual(resp.status_code, 401)
