"""
Tests for the claims module.

Covers claim creation, status transitions, document upload,
and claim number generation.
"""

from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase

from claims.models import Claim, ClaimDocument
from claims.service import ClaimService
from claims.schemas import ClaimCreateSchema
from tests.factories import (
    create_test_claim,
    create_test_policy,
    setup_user_with_org,
)


class ClaimModelTest(TestCase):
    """Tests for the Claim model."""

    def test_claim_number_auto_generated(self):
        claim = create_test_claim()
        self.assertIsNotNone(claim.claim_number)
        self.assertTrue(claim.claim_number.startswith("CLM-"))

    def test_claim_number_unique(self):
        c1 = create_test_claim()
        c2 = create_test_claim()
        self.assertNotEqual(c1.claim_number, c2.claim_number)

    def test_claim_str_representation(self):
        claim = create_test_claim()
        self.assertTrue(str(claim).startswith("Claim CLM-"))

    def test_claim_default_status_is_submitted(self):
        claim = create_test_claim()
        self.assertEqual(claim.status, "submitted")


class ClaimStatusTransitionsTest(TestCase):
    """Tests for claim status lifecycle transitions."""

    def test_submitted_to_under_review(self):
        claim = create_test_claim(status="submitted")
        claim.status = "under_review"
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, "under_review")

    def test_under_review_to_approved(self):
        claim = create_test_claim(status="under_review")
        claim.status = "approved"
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, "approved")

    def test_under_review_to_denied(self):
        claim = create_test_claim(status="under_review")
        claim.status = "denied"
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, "denied")

    def test_approved_to_closed(self):
        claim = create_test_claim(status="approved")
        claim.status = "closed"
        claim.save()
        claim.refresh_from_db()
        self.assertEqual(claim.status, "closed")


class ClaimFinancialFieldsTest(TestCase):
    """Tests for claim financial tracking fields."""

    def test_financial_fields_can_be_set(self):
        claim = create_test_claim()
        claim.paid_loss = Decimal("5000.00")
        claim.paid_lae = Decimal("1000.00")
        claim.case_reserve_loss = Decimal("10000.00")
        claim.case_reserve_lae = Decimal("2000.00")
        claim.save()

        claim.refresh_from_db()
        self.assertEqual(claim.paid_loss, Decimal("5000.00"))
        self.assertEqual(claim.paid_lae, Decimal("1000.00"))
        self.assertEqual(claim.case_reserve_loss, Decimal("10000.00"))
        self.assertEqual(claim.case_reserve_lae, Decimal("2000.00"))

    def test_financial_fields_null_by_default(self):
        claim = create_test_claim()
        self.assertIsNone(claim.paid_loss)
        self.assertIsNone(claim.paid_lae)
        self.assertIsNone(claim.case_reserve_loss)
        self.assertIsNone(claim.case_reserve_lae)


class ClaimServiceSubmitTest(TestCase):
    """Tests for ClaimService.submit_claim."""

    @patch("claims.service.S3Service")
    @patch("claims.service.EmailService")
    def test_submit_claim_creates_claim(self, mock_email, mock_s3):
        user, org = setup_user_with_org()
        policy = create_test_policy(
            quote=create_test_policy.__wrapped__ if False else None,  # Use default
        )
        # Override to use our org
        quote = policy.quote
        quote.organization = org
        quote.save()

        policy_for_claim = create_test_policy(
            quote=quote,
        )

        data = ClaimCreateSchema(
            policy_id=policy_for_claim.id,
            organization_name="Acme Tech",
            first_name="John",
            last_name="Doe",
            email="john@acme.com",
            phone_number="5551234567",
            description="Water damage to server room",
        )

        claim = ClaimService.submit_claim(data, files=None, user=user)

        self.assertEqual(claim.status, "submitted")
        self.assertEqual(claim.organization_id, org.id)
        self.assertTrue(claim.claim_number.startswith("CLM-"))
        self.assertEqual(claim.description, "Water damage to server room")

    @patch("claims.service.S3Service")
    @patch("claims.service.EmailService")
    def test_submit_claim_with_documents(self, mock_email, mock_s3):
        mock_s3.upload_file.return_value = {
            "s3_key": "claims/1/docs/test.pdf",
            "s3_url": "https://s3.amazonaws.com/test.pdf",
        }
        user, org = setup_user_with_org()
        quote = create_test_policy().quote
        quote.organization = org
        quote.save()
        policy = create_test_policy(quote=quote)

        mock_file = MagicMock()
        mock_file.name = "evidence.pdf"
        mock_file.read.return_value = b"PDF content"
        mock_file.size = 100
        mock_file.content_type = "application/pdf"

        data = ClaimCreateSchema(
            policy_id=policy.id,
            organization_name="Acme Tech",
            first_name="Jane",
            last_name="Smith",
            email="jane@acme.com",
            phone_number="5559876543",
            description="Equipment damage",
        )

        claim = ClaimService.submit_claim(data, files=[mock_file], user=user)
        docs = ClaimDocument.objects.filter(claim=claim)
        self.assertEqual(docs.count(), 1)


class ClaimServiceGetTest(TestCase):
    """Tests for ClaimService retrieval methods."""

    @patch("claims.service.EmailService")
    def test_get_user_claims_returns_org_scoped(self, mock_email):
        user, org = setup_user_with_org()
        policy = create_test_policy()
        policy.quote.organization = org
        policy.quote.save()

        Claim.objects.create(
            user=user,
            organization=org,
            policy=policy,
            organization_name="Test Org",
            first_name="Test",
            last_name="User",
            email="test@test.com",
            phone_number="5551234567",
            description="Test claim",
        )

        claims = ClaimService.get_user_claims(user)
        self.assertEqual(len(claims), 1)

    def test_get_claim_by_number(self):
        user, org = setup_user_with_org()
        policy = create_test_policy()
        policy.quote.organization = org
        policy.quote.save()

        claim = Claim.objects.create(
            user=user,
            organization=org,
            policy=policy,
            organization_name="Test",
            first_name="Test",
            last_name="User",
            email="t@t.com",
            phone_number="555",
            description="Test",
        )

        found = ClaimService.get_claim_by_number(claim.claim_number, user)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, claim.id)

    def test_get_claim_by_number_wrong_org_returns_none(self):
        user1, org1 = setup_user_with_org()
        user2, org2 = setup_user_with_org()
        policy = create_test_policy()
        policy.quote.organization = org1
        policy.quote.save()

        claim = Claim.objects.create(
            user=user1,
            organization=org1,
            policy=policy,
            organization_name="Test",
            first_name="Test",
            last_name="User",
            email="t@t.com",
            phone_number="555",
            description="Test",
        )

        found = ClaimService.get_claim_by_number(claim.claim_number, user2)
        self.assertIsNone(found)
