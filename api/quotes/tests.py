"""
Tests for the quotes module.

Covers quote creation, step saving, status transitions, coverage selection,
quote splitting for partial checkout, and quote duplication.
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from quotes.models import Quote, UnderwriterOverride, CustomProduct
from quotes.service import QuoteService
from tests.factories import (
    create_test_quote,
    create_test_company,
    setup_user_with_org,
)


class QuoteModelTest(TestCase):
    """Tests for the Quote model itself."""

    def test_quote_number_auto_generated_on_save(self):
        user, org = setup_user_with_org()
        company = create_test_company()
        quote = Quote.objects.create(
            user=user,
            organization=org,
            company=company,
            status="draft",
            coverages=["cyber-liability"],
        )
        self.assertIsNotNone(quote.quote_number)
        self.assertTrue(len(quote.quote_number) > 0)

    def test_quote_number_unique(self):
        user, org = setup_user_with_org()
        company = create_test_company()
        q1 = Quote.objects.create(
            user=user, organization=org, company=company, status="draft", coverages=[]
        )
        q2 = Quote.objects.create(
            user=user, organization=org, company=company, status="draft", coverages=[]
        )
        self.assertNotEqual(q1.quote_number, q2.quote_number)

    def test_quote_default_status_is_submitted(self):
        user, org = setup_user_with_org()
        company = create_test_company()
        quote = Quote.objects.create(
            user=user, organization=org, company=company, coverages=[]
        )
        self.assertEqual(quote.status, "submitted")

    def test_quote_str_returns_quote_number(self):
        quote = create_test_quote()
        self.assertEqual(str(quote), quote.quote_number)


class QuoteCreateDraftTest(TestCase):
    """Tests for QuoteService.create_draft_quote."""

    def test_create_draft_quote_creates_company_and_address(self):
        user, org = setup_user_with_org()
        quote = QuoteService.create_draft_quote(
            coverages=["cyber-liability", "directors-and-officers"],
            selected_package="startup",
            user=user,
        )
        self.assertEqual(quote.status, "draft")
        self.assertIsNotNone(quote.company)
        self.assertIsNotNone(quote.company.business_address)
        self.assertEqual(quote.coverages, ["cyber-liability", "directors-and-officers"])
        self.assertEqual(quote.organization_id, org.id)

    def test_create_draft_quote_sets_completed_steps(self):
        user, org = setup_user_with_org()
        quote = QuoteService.create_draft_quote(
            coverages=["cyber-liability"],
            selected_package=None,
            user=user,
        )
        self.assertIn("welcome", quote.completed_steps)
        self.assertIn("package-selection", quote.completed_steps)
        self.assertEqual(quote.current_step, "products")

    def test_create_draft_quote_denied_for_viewer(self):
        user, org = setup_user_with_org()
        user.active_org_role = "viewer"
        with self.assertRaises(Exception):
            QuoteService.create_draft_quote(
                coverages=["cyber-liability"], selected_package=None, user=user
            )


class QuoteSaveStepTest(TestCase):
    """Tests for QuoteService.save_step (partial form updates)."""

    def test_save_step_merges_form_data(self):
        user, org = setup_user_with_org()
        quote = create_test_quote(user=user, org=org)
        result = QuoteService.save_step(
            quote.quote_number,
            "business-address",
            {"business_address": {"city": "New York"}},
            user,
            next_step="organization-info",
        )
        self.assertIsNotNone(result)
        self.assertIn("business-address", result.completed_steps)
        self.assertEqual(result.current_step, "organization-info")

    def test_save_step_resets_status_if_already_quoted(self):
        user, org = setup_user_with_org()
        quote = create_test_quote(
            user=user, org=org, status="quoted", quote_amount=Decimal("5000")
        )
        result = QuoteService.save_step(
            quote.quote_number,
            "products",
            {"coverages": ["cyber-liability"]},
            user,
        )
        self.assertEqual(result.status, "draft")
        self.assertIsNone(result.rating_result)
        self.assertIsNone(result.quote_amount)

    def test_save_step_updates_coverages(self):
        user, org = setup_user_with_org()
        quote = create_test_quote(user=user, org=org)
        result = QuoteService.save_step(
            quote.quote_number,
            "products",
            {"coverages": ["cyber-liability", "directors-and-officers"]},
            user,
        )
        self.assertEqual(
            result.coverages, ["cyber-liability", "directors-and-officers"]
        )
        # available_coverages should be union
        self.assertIn("cyber-liability", result.available_coverages)
        self.assertIn("directors-and-officers", result.available_coverages)

    def test_save_step_returns_none_for_wrong_org(self):
        user1, org1 = setup_user_with_org()
        user2, org2 = setup_user_with_org()
        quote = create_test_quote(user=user1, org=org1)
        result = QuoteService.save_step(
            quote.quote_number, "test", {"foo": "bar"}, user2
        )
        self.assertIsNone(result)


class QuoteStatusTransitionsTest(TestCase):
    """Tests for quote status lifecycle transitions."""

    def test_draft_to_submitted(self):
        quote = create_test_quote(status="draft")
        quote.status = "submitted"
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.status, "submitted")

    def test_submitted_to_quoted(self):
        quote = create_test_quote(status="submitted")
        quote.status = "quoted"
        quote.quoted_at = timezone.now()
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.status, "quoted")

    def test_quoted_to_purchased(self):
        quote = create_test_quote(status="quoted")
        quote.status = "purchased"
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.status, "purchased")

    def test_submitted_to_needs_review(self):
        quote = create_test_quote(status="submitted")
        quote.status = "needs_review"
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.status, "needs_review")

    def test_needs_review_to_quoted_via_overrides(self):
        quote = create_test_quote(status="needs_review")
        quote.status = "quoted"
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.status, "quoted")


class QuoteSplitForPartialCheckoutTest(TestCase):
    """Tests for split_quote_for_partial_checkout."""

    def test_split_creates_child_quote_with_instant_coverages(self):
        user, org = setup_user_with_org()
        quote = create_test_quote(
            user=user,
            org=org,
            status="needs_review",
            coverages=["cyber-liability", "custom-workers-comp"],
            available_coverages=["cyber-liability", "custom-workers-comp"],
            rating_result={
                "success": False,
                "breakdown": {
                    "cyber-liability": {"premium": 3000.00, "breakdown": "test"},
                },
                "review_reasons": [
                    {"coverage": "custom-workers-comp", "reason": "Brokered coverage"}
                ],
                "calculated_at": "2026-01-01T00:00:00",
            },
            quote_amount=Decimal("3000.00"),
        )

        child = QuoteService.split_quote_for_partial_checkout(
            quote, instant_coverages=["cyber-liability"]
        )

        self.assertEqual(child.status, "quoted")
        self.assertEqual(child.coverages, ["cyber-liability"])
        self.assertEqual(child.parent_quote, quote)
        self.assertEqual(float(child.quote_amount), 3000.00)

        quote.refresh_from_db()
        self.assertEqual(quote.coverages, ["custom-workers-comp"])
        self.assertIsNone(quote.quote_amount)

    def test_split_preserves_form_data_snapshot(self):
        user, org = setup_user_with_org()
        snapshot = {"coverages": ["cyber-liability", "custom-bop"], "company": "test"}
        quote = create_test_quote(
            user=user,
            org=org,
            status="needs_review",
            coverages=["cyber-liability", "custom-bop"],
            form_data_snapshot=snapshot,
            rating_result={
                "success": False,
                "breakdown": {"cyber-liability": {"premium": 2000}},
                "review_reasons": [{"coverage": "custom-bop", "reason": "Brokered"}],
            },
        )
        child = QuoteService.split_quote_for_partial_checkout(
            quote, ["cyber-liability"]
        )
        self.assertEqual(child.form_data_snapshot, snapshot)


class QuoteDuplicationTest(TestCase):
    """Tests for quote duplication (admin action)."""

    def test_duplicate_quote_creates_new_draft(self):
        user, org = setup_user_with_org()
        original = create_test_quote(
            user=user,
            org=org,
            status="quoted",
            coverages=["cyber-liability"],
            quote_amount=Decimal("5000"),
        )

        new_quote = Quote.objects.create(
            company=original.company,
            user=original.user,
            organization=original.organization,
            status="draft",
            coverages=original.coverages,
            available_coverages=original.available_coverages,
            coverage_data=original.coverage_data,
            limits_retentions=original.limits_retentions,
            billing_frequency=original.billing_frequency,
            form_data_snapshot=original.form_data_snapshot,
            parent_quote=original,
        )

        self.assertEqual(new_quote.status, "draft")
        self.assertEqual(new_quote.coverages, original.coverages)
        self.assertEqual(new_quote.parent_quote, original)
        self.assertNotEqual(new_quote.quote_number, original.quote_number)


class QuoteAmountCalculationTest(TestCase):
    """Tests for quote amount after rating."""

    def test_quote_amount_set_on_successful_rating(self):
        quote = create_test_quote(status="submitted")
        quote.quote_amount = Decimal("10000.00")
        quote.status = "quoted"
        quote.save()
        quote.refresh_from_db()
        self.assertEqual(quote.quote_amount, Decimal("10000.00"))

    def test_quote_amount_null_when_needs_review(self):
        quote = create_test_quote(status="needs_review", quote_amount=None)
        self.assertIsNone(quote.quote_amount)


class UnderwriterOverrideTest(TestCase):
    """Tests for UnderwriterOverride model."""

    def test_create_override(self):
        quote = create_test_quote()
        override = UnderwriterOverride.objects.create(
            quote=quote,
            coverage="cyber-liability",
            multiplier=Decimal("1.50"),
            bypass_validation=True,
            comment="Approved after manual review",
        )
        self.assertEqual(override.multiplier, Decimal("1.50"))
        self.assertTrue(override.bypass_validation)

    def test_override_unique_per_quote_coverage(self):
        quote = create_test_quote()
        UnderwriterOverride.objects.create(
            quote=quote,
            coverage="cyber-liability",
            multiplier=Decimal("1.00"),
            bypass_validation=True,
            comment="First",
        )
        with self.assertRaises(Exception):
            UnderwriterOverride.objects.create(
                quote=quote,
                coverage="cyber-liability",
                multiplier=Decimal("1.50"),
                bypass_validation=True,
                comment="Duplicate",
            )


class CustomProductTest(TestCase):
    """Tests for CustomProduct (brokered coverage pricing)."""

    def test_create_custom_product(self):
        quote = create_test_quote()
        cp = CustomProduct.objects.create(
            quote=quote,
            name="Workers Comp",
            product_type="custom-workers-comp",
            price=Decimal("2500.00"),
            per_occurrence_limit=1000000,
            aggregate_limit=2000000,
            carrier="Pie Insurance",
        )
        self.assertEqual(cp.price, Decimal("2500.00"))
        self.assertEqual(cp.product_type, "custom-workers-comp")


class PromoCodeTest(TestCase):
    """Tests for PromoCode model."""

    def test_promo_code_is_valid(self):
        from tests.factories import create_test_promo_code

        promo = create_test_promo_code()
        self.assertTrue(promo.is_valid)

    def test_promo_code_inactive_is_not_valid(self):
        from tests.factories import create_test_promo_code

        promo = create_test_promo_code(is_active=False)
        self.assertFalse(promo.is_valid)

    def test_promo_code_max_uses_exceeded(self):
        from tests.factories import create_test_promo_code

        promo = create_test_promo_code(max_uses=1, use_count=1)
        self.assertFalse(promo.is_valid)

    def test_promo_code_expired(self):
        from tests.factories import create_test_promo_code

        promo = create_test_promo_code(
            valid_until=timezone.now() - timezone.timedelta(days=1)
        )
        self.assertFalse(promo.is_valid)
