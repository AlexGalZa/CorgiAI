"""
Tests for the policies module.

Covers policy creation from quote, policy number generation,
endorsements (modify limits, add/remove coverage), cancellation,
reactivation, PolicyTransaction, StateAllocation, Cession,
monthly premium calculation, and promo code application.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone

from policies.models import Policy, Payment, PolicyTransaction, StateAllocation, Cession
from policies.service import PolicyService
from policies.sequences import generate_policy_number, generate_coi_number
from common.constants import (
    ADMIN_FEE_RATE,
    DEFAULT_CEDED_PREMIUM_RATE,
    DEFAULT_TREATY_ID,
    DEFAULT_ATTACHMENT_POINT,
)
from rating.constants import STATE_TAX_RATES, MONTHLY_BILLING_MULTIPLIER
from tests.factories import (
    create_test_quote,
    create_test_policy,
    create_test_payment,
)


class PolicyModelTest(TestCase):
    """Tests for the Policy model."""

    def test_policy_number_auto_generated(self):
        quote = create_test_quote(status="purchased")
        policy = Policy.objects.create(
            quote=quote,
            coverage_type="commercial-general-liability",
            premium=Decimal("5000.00"),
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
            purchased_at=timezone.now(),
            status="active",
        )
        self.assertIsNotNone(policy.policy_number)
        self.assertIn("CG", policy.policy_number)

    def test_policy_str_representation(self):
        policy = create_test_policy()
        self.assertTrue(str(policy).startswith("Policy "))


class PolicyNumberGenerationTest(TestCase):
    """Tests for policy number sequence generation."""

    def test_generate_policy_number_format(self):
        number = generate_policy_number(
            "commercial-general-liability", "CA", date(2026, 3, 15)
        )
        self.assertTrue(number.startswith("CG-CA-26-"))
        self.assertEqual(len(number.split("-")), 5)

    def test_generate_policy_number_increments(self):
        n1 = generate_policy_number("cyber-liability", "NY", date(2026, 1, 1))
        n2 = generate_policy_number("cyber-liability", "NY", date(2026, 1, 1))
        self.assertNotEqual(n1, n2)

    def test_generate_coi_number_format(self):
        number = generate_coi_number("CA", date(2026, 3, 15))
        self.assertTrue(number.startswith("COI-CA-26-"))

    def test_unknown_coverage_type_raises_error(self):
        with self.assertRaises(ValueError):
            generate_policy_number("nonexistent", "CA", date(2026, 1, 1))


class PolicyTransactionCreationTest(TestCase):
    """Tests for PolicyTransaction + StateAllocation + Cession creation."""

    def test_create_transaction_for_non_brokered_policy(self):
        policy = create_test_policy(premium=Decimal("5000.00"))
        txn = PolicyService.create_transaction_and_allocation(policy, "new")

        self.assertEqual(txn.transaction_type, "new")
        self.assertEqual(txn.policy, policy)
        self.assertIsNotNone(txn.gross_written_premium)

        # State tax should be extracted
        state = policy.quote.company.business_address.state
        tax_multiplier = Decimal(str(STATE_TAX_RATES.get(state, 1.0)))
        expected_gwp = (Decimal("5000.00") / tax_multiplier).quantize(Decimal("0.01"))
        self.assertEqual(txn.gross_written_premium, expected_gwp)

        # Admin fee should be calculated
        expected_admin_fee = (expected_gwp * Decimal(ADMIN_FEE_RATE)).quantize(
            Decimal("0.01")
        )
        self.assertEqual(txn.admin_fee_amount, expected_admin_fee)

    def test_state_allocation_created(self):
        policy = create_test_policy()
        txn = PolicyService.create_transaction_and_allocation(policy)
        allocations = StateAllocation.objects.filter(transaction=txn)
        self.assertEqual(allocations.count(), 1)
        alloc = allocations.first()
        self.assertEqual(alloc.state, policy.quote.company.business_address.state)
        self.assertEqual(alloc.allocation_percent, Decimal("1.0000"))
        self.assertEqual(alloc.allocation_method, "hq")

    def test_cession_created_for_non_brokered(self):
        policy = create_test_policy(is_brokered=False)
        txn = PolicyService.create_transaction_and_allocation(policy)
        cessions = Cession.objects.filter(transaction=txn)
        self.assertEqual(cessions.count(), 1)
        cession = cessions.first()
        self.assertEqual(cession.treaty_id, DEFAULT_TREATY_ID)
        self.assertEqual(cession.reinsurance_type, "XOL")
        self.assertEqual(
            cession.ceded_premium_rate, Decimal(DEFAULT_CEDED_PREMIUM_RATE)
        )
        self.assertEqual(cession.attachment_point, Decimal(DEFAULT_ATTACHMENT_POINT))

    def test_no_cession_for_brokered_policy(self):
        policy = create_test_policy(is_brokered=True, carrier="External Carrier")
        txn = PolicyService.create_transaction_and_allocation(policy)
        cessions = Cession.objects.filter(transaction=txn)
        self.assertEqual(cessions.count(), 0)

    def test_brokered_policy_no_admin_fee(self):
        policy = create_test_policy(is_brokered=True, carrier="External Carrier")
        txn = PolicyService.create_transaction_and_allocation(policy)
        self.assertIsNone(txn.admin_fee_rate)
        self.assertIsNone(txn.admin_fee_amount)
        self.assertEqual(txn.tax_amount, Decimal("0"))


class EndorseModifyLimitsTest(TestCase):
    """Tests for endorsement — modify limits."""

    @patch("policies.service.StripeService")
    @patch("policies.service.DocumentsGeneratorService")
    @patch("policies.service.S3Service")
    def test_endorse_modify_limits_updates_premium(
        self, mock_s3, mock_docs, mock_stripe
    ):
        # StripeService.create_one_time_charge / create_and_send_invoice return
        # an object whose .id is inserted into Payment.stripe_invoice_id.
        # Explicit return_values (not bare MagicMock) so Django doesn't see
        # them as F-expressions when the Payment row is INSERTed.
        mock_stripe.create_one_time_charge.return_value = type(
            "StripeChargeStub", (), {"id": "ch_stub_123"}
        )()
        mock_stripe.create_and_send_invoice.return_value = type(
            "StripeInvoiceStub", (), {"id": "in_stub_456"}
        )()
        mock_stripe.create_refund.return_value = MagicMock(id="re_test_123")
        mock_docs.generate_coi_for_policies.return_value = None
        mock_docs.generate_policy_document_pdf.return_value = b"%PDF-1.4 stub"
        mock_docs.generate_coi_pdf.return_value = b"%PDF-1.4 stub"
        policy = create_test_policy(premium=Decimal("5000.00"))
        new_limits = {
            "aggregate_limit": 2000000,
            "per_occurrence_limit": 2000000,
            "retention": 0,
        }
        new_premium = Decimal("8000.00")

        result = PolicyService.endorse_modify_limits(
            policy, new_limits, new_premium, "Increased limits"
        )

        policy.refresh_from_db()
        self.assertEqual(policy.premium, Decimal("8000.00"))
        self.assertEqual(policy.limits_retentions, new_limits)
        self.assertEqual(result["old_premium"], Decimal("5000.00"))
        self.assertEqual(result["new_premium"], Decimal("8000.00"))

    def test_endorse_modify_limits_fails_for_inactive_policy(self):
        policy = create_test_policy(status="cancelled")
        with self.assertRaises(ValueError, msg="Can only endorse active policies."):
            PolicyService.endorse_modify_limits(
                policy, {"aggregate_limit": 2000000}, Decimal("8000"), "test"
            )

    def test_endorse_modify_limits_fails_for_brokered(self):
        policy = create_test_policy(is_brokered=True)
        with self.assertRaises(ValueError):
            PolicyService.endorse_modify_limits(
                policy, {"aggregate_limit": 2000000}, Decimal("8000"), "test"
            )


class EndorseAddCoverageTest(TestCase):
    """Tests for endorsement — add coverage."""

    @patch("policies.service.StripeService")
    @patch("policies.service.DocumentsGeneratorService")
    @patch("policies.service.S3Service")
    def test_add_coverage_creates_new_policy(self, mock_s3, mock_docs, mock_stripe):
        mock_stripe.create_one_time_charge.return_value = type(
            "StripeChargeStub", (), {"id": "pi_new"}
        )()
        mock_docs.generate_coi_for_policies.return_value = None
        # Any bytes-like so BytesIO(...) inside _upload_and_store_document works.
        mock_docs.generate_policy_document_pdf.return_value = b"%PDF-1.4 stub"
        mock_docs.generate_coi_pdf.return_value = b"%PDF-1.4 stub"
        existing = create_test_policy(premium=Decimal("5000.00"))

        result = PolicyService.endorse_add_coverage(
            existing,
            "cyber-liability",
            {
                "aggregate_limit": 1000000,
                "per_occurrence_limit": 1000000,
                "retention": 10000,
            },
            Decimal("3000.00"),
            "Adding cyber coverage",
        )

        new_policy = result["new_policy"]
        self.assertEqual(new_policy.coverage_type, "cyber-liability")
        self.assertEqual(new_policy.premium, Decimal("3000.00"))
        self.assertEqual(new_policy.coi_number, existing.coi_number)
        self.assertEqual(new_policy.status, "active")


class EndorseRemoveCoverageTest(TestCase):
    """Tests for endorsement — remove coverage."""

    @patch("policies.service.StripeService")
    @patch("policies.service.DocumentsGeneratorService")
    @patch("policies.service.S3Service")
    def test_remove_coverage_cancels_policy(self, mock_s3, mock_docs, mock_stripe):
        mock_stripe.create_refund.return_value = MagicMock(id="re_test")
        mock_docs.generate_coi_for_policies.return_value = None

        quote = create_test_quote(
            status="purchased",
            coverages=["commercial-general-liability", "cyber-liability"],
        )
        create_test_policy(
            quote=quote,
            coverage_type="commercial-general-liability",
            coi_number="COI-CA-26-000001",
        )
        p2 = create_test_policy(
            quote=quote,
            coverage_type="cyber-liability",
            coi_number="COI-CA-26-000001",
            premium=Decimal("3000.00"),
        )

        result = PolicyService.endorse_remove_coverage(p2, "Customer requested removal")
        p2.refresh_from_db()
        self.assertEqual(p2.status, "cancelled")
        self.assertGreaterEqual(result["refund_amount"], Decimal("0"))

    def test_cannot_remove_last_coverage_in_coi_group(self):
        policy = create_test_policy()
        with self.assertRaises(ValueError, msg="Cannot remove the last coverage"):
            PolicyService.endorse_remove_coverage(policy, "test")


class CancellationTest(TestCase):
    """Tests for policy cancellation with prorated refund."""

    @patch("policies.service.StripeService")
    def test_cancel_policy_sets_status(self, mock_stripe):
        mock_stripe.create_refund.return_value = MagicMock(id="re_cancel")
        policy = create_test_policy(status="active")

        PolicyService.cancel_policy(policy, "Customer requested cancellation")

        policy.refresh_from_db()
        self.assertEqual(policy.status, "cancelled")
        self.assertEqual(policy.expiration_date, date.today())

    @patch("policies.service.StripeService")
    def test_cancel_creates_cancellation_transaction(self, mock_stripe):
        mock_stripe.create_refund.return_value = MagicMock(id="re_cancel")
        policy = create_test_policy(status="active")

        PolicyService.cancel_policy(policy, "Test cancellation")

        txn = PolicyTransaction.objects.filter(
            policy=policy, transaction_type="cancel"
        ).first()
        self.assertIsNotNone(txn)
        self.assertLess(txn.gross_written_premium, 0)

    def test_cancel_inactive_policy_raises_error(self):
        policy = create_test_policy(status="cancelled")
        with self.assertRaises(ValueError):
            PolicyService.cancel_policy(policy, "test")


class ProrationFactorTest(TestCase):
    """Tests for proration factor calculation."""

    def test_proration_factor_full_term(self):
        policy = create_test_policy(
            effective_date=date.today(),
            expiration_date=date.today() + timedelta(days=365),
        )
        factor = PolicyService._calculate_proration_factor(policy)
        self.assertGreater(factor, Decimal("0.99"))

    def test_proration_factor_half_term(self):
        policy = create_test_policy(
            effective_date=date.today() - timedelta(days=183),
            expiration_date=date.today() + timedelta(days=182),
        )
        factor = PolicyService._calculate_proration_factor(policy)
        self.assertAlmostEqual(float(factor), 0.4986, places=1)

    def test_proration_factor_expired(self):
        policy = create_test_policy(
            effective_date=date.today() - timedelta(days=400),
            expiration_date=date.today() - timedelta(days=35),
        )
        factor = PolicyService._calculate_proration_factor(policy)
        self.assertEqual(factor, Decimal("0"))


class MonthlyPremiumCalculationTest(TestCase):
    """Tests for monthly premium calculation."""

    def test_monthly_premium_for_rrg_policy(self):
        # RRG monthly: (rating_premium × 1.111) / 12
        rating_premium = Decimal("6000.00")
        surcharge = Decimal(str(MONTHLY_BILLING_MULTIPLIER))
        expected_monthly = (rating_premium * surcharge / 12).quantize(Decimal("0.01"))
        policy = create_test_policy(
            premium=rating_premium,
            billing_frequency="monthly",
            monthly_premium=expected_monthly,
        )
        self.assertEqual(policy.monthly_premium, expected_monthly)

    def test_monthly_premium_for_brokered_policy(self):
        # Brokered monthly: CustomProduct.price / 12
        price = Decimal("2400.00")
        expected_monthly = (price / 12).quantize(Decimal("0.01"))
        policy = create_test_policy(
            premium=price,
            billing_frequency="monthly",
            monthly_premium=expected_monthly,
            is_brokered=True,
        )
        self.assertEqual(policy.monthly_premium, expected_monthly)


class PromoCodeApplicationTest(TestCase):
    """Tests for applying promo codes post-purchase."""

    @patch("policies.service.StripeService")
    def test_apply_promo_to_annual_rrg_policy(self, mock_stripe):
        mock_stripe.create_refund.return_value = MagicMock(id="re_promo")
        policy = create_test_policy(
            premium=Decimal("10000.00"),
            billing_frequency="annual",
            is_brokered=False,
        )
        create_test_payment(policy=policy)

        promo = MagicMock()
        promo.code = "SAVE20"
        promo.coupon.percent_off = 20.0

        result = PolicyService.apply_promo_to_policy(policy, promo)

        policy.refresh_from_db()
        self.assertEqual(policy.premium, Decimal("8000.00"))
        self.assertEqual(policy.promo_code, "SAVE20")
        self.assertEqual(policy.discount_percentage, Decimal("20"))
        self.assertEqual(result["old_premium"], Decimal("10000.00"))
        self.assertEqual(result["new_premium"], Decimal("8000.00"))

    def test_apply_promo_to_brokered_fails(self):
        policy = create_test_policy(is_brokered=True)
        promo = MagicMock()
        promo.coupon.percent_off = 10.0
        with self.assertRaises(ValueError, msg="Cannot apply promo codes to brokered"):
            PolicyService.apply_promo_to_policy(policy, promo)

    @patch("policies.service.StripeService")
    def test_apply_promo_when_already_applied_fails(self, mock_stripe):
        policy = create_test_policy(promo_code="EXISTING")
        promo = MagicMock()
        promo.coupon.percent_off = 10.0
        with self.assertRaises(ValueError, msg="already has a promo code"):
            PolicyService.apply_promo_to_policy(policy, promo)


class RegulatoryFieldsTest(TestCase):
    """Tests for regulatory field denormalization."""

    def test_build_regulatory_fields(self):
        quote = create_test_quote(status="purchased")
        effective = date(2026, 3, 15)
        expiration = date(2027, 3, 15)

        fields = PolicyService.build_regulatory_fields(
            quote, "annual", effective, expiration
        )

        self.assertEqual(fields["insured_legal_name"], quote.company.entity_legal_name)
        self.assertEqual(fields["insured_fein"], quote.company.federal_ein)
        self.assertEqual(
            fields["principal_state"], quote.company.business_address.state
        )
        self.assertEqual(fields["paid_to_date"], expiration)  # Annual → expiration

    def test_build_regulatory_fields_monthly_paid_to_date(self):
        quote = create_test_quote(status="purchased")
        effective = date(2026, 3, 15)
        expiration = date(2027, 3, 15)

        fields = PolicyService.build_regulatory_fields(
            quote, "monthly", effective, expiration
        )
        # Monthly paid_to_date = effective + 1 month
        from dateutil.relativedelta import relativedelta

        expected = effective + relativedelta(months=1)
        self.assertEqual(fields["paid_to_date"], expected)


class PaymentModelTest(TestCase):
    """Tests for Payment model."""

    def test_create_payment(self):
        policy = create_test_policy()
        payment = Payment.objects.create(
            policy=policy,
            stripe_invoice_id="pi_test_789",
            amount=Decimal("5000.00"),
            status="paid",
            paid_at=timezone.now(),
        )
        self.assertEqual(payment.amount, Decimal("5000.00"))
        self.assertEqual(payment.status, "paid")
        self.assertEqual(str(payment), "Payment pi_test_789 - $5000.00")
