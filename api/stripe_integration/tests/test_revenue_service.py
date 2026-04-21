"""
Unit tests for stripe_integration.revenue_service.revenue_split.

Covers the brokered flow (100% to corgi_admin) and the non-brokered 4-way
split (22 / 46.7 / 28.3 / 3), plus tax routing to techrrg and fee routing
to admin_fee. These tests deliberately use lightweight duck-typed stand-ins
for ``payment`` and ``policy`` — revenue_service only reads attributes off
them, so we can keep the test surface small and DB-free.
"""

from decimal import Decimal
from types import SimpleNamespace


from stripe_integration.revenue_service import (
    CORGI_ADMIN_RATE,
    CORGIRE_RATE,
    DANE_RATE,
    TECHRRG_RATE,
    revenue_split,
)


def _payment(
    *,
    premium="0",
    tax="0",
    policy_fee="0",
    membership_fee="0",
    admin_fee="0",
):
    return SimpleNamespace(
        gross_written_premium=Decimal(premium),
        tax_amount=Decimal(tax),
        policy_fee_delta=Decimal(policy_fee),
        membership_fee_delta=Decimal(membership_fee),
        admin_fee_amount=Decimal(admin_fee),
    )


def _policy(is_brokered=False, policy_number="POL-TEST-001"):
    return SimpleNamespace(is_brokered=is_brokered, policy_number=policy_number)


# ── Brokered flow ────────────────────────────────────────────────────


def test_brokered_routes_entire_premium_to_corgi_admin():
    payment = _payment(premium="1000.00")
    policy = _policy(is_brokered=True)

    buckets = revenue_split(payment, policy)

    assert buckets["corgi_admin"] == Decimal("1000.00")
    assert buckets["techrrg"] == Decimal("0.00")
    assert buckets["corgire"] == Decimal("0.00")
    assert buckets["dane"] == Decimal("0.00")


def test_brokered_admin_fee_bucket_sums_tax_plus_fees():
    payment = _payment(
        premium="1000.00",
        tax="75.00",
        policy_fee="25.00",
        membership_fee="10.00",
        admin_fee="5.00",
    )
    policy = _policy(is_brokered=True)

    buckets = revenue_split(payment, policy)

    # All tax + fees should end up in admin_fee; premium untouched in corgi_admin.
    assert buckets["corgi_admin"] == Decimal("1000.00")
    # 75 + 25 + 10 + 5 = 115
    assert buckets["admin_fee"] == Decimal("115.00")


def test_brokered_with_zero_premium_returns_all_zero():
    payment = _payment()
    policy = _policy(is_brokered=True)

    buckets = revenue_split(payment, policy)

    assert all(amount == Decimal("0.00") for amount in buckets.values())


# ── Non-brokered flow ────────────────────────────────────────────────


def test_non_brokered_splits_premium_across_four_buckets():
    payment = _payment(premium="1000.00")
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    assert buckets["corgi_admin"] == Decimal("220.00")  # 22.0%
    assert buckets["techrrg"] == Decimal("467.00")  # 46.7%
    assert buckets["corgire"] == Decimal("283.00")  # 28.3%
    assert buckets["dane"] == Decimal("30.00")  # 3.0%


def test_non_brokered_splits_sum_to_premium_when_no_rounding_loss():
    payment = _payment(premium="1000.00")
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)
    total = (
        buckets["corgi_admin"]
        + buckets["techrrg"]
        + buckets["corgire"]
        + buckets["dane"]
    )
    assert total == Decimal("1000.00")


def test_non_brokered_rates_match_canonical_constants():
    # Guardrail: if someone updates the constants without noticing these tests.
    assert CORGI_ADMIN_RATE == Decimal("0.220")
    assert TECHRRG_RATE == Decimal("0.467")
    assert CORGIRE_RATE == Decimal("0.283")
    assert DANE_RATE == Decimal("0.030")
    assert CORGI_ADMIN_RATE + TECHRRG_RATE + CORGIRE_RATE + DANE_RATE == Decimal(
        "1.000"
    )


def test_non_brokered_tax_routes_to_techrrg_not_admin_fee():
    payment = _payment(premium="1000.00", tax="50.00")
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    # 46.7% of 1000 = 467.00; + 50 tax = 517.00
    assert buckets["techrrg"] == Decimal("517.00")
    # admin_fee gets only policy/membership/admin fees — not tax in non-brokered.
    assert buckets["admin_fee"] == Decimal("0.00")


def test_non_brokered_policy_and_membership_fees_route_to_admin_fee():
    payment = _payment(
        premium="1000.00",
        policy_fee="15.00",
        membership_fee="5.00",
        admin_fee="2.50",
    )
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    # 15 + 5 + 2.50 = 22.50
    assert buckets["admin_fee"] == Decimal("22.50")
    # Tax is 0, so techrrg is plain 46.7%
    assert buckets["techrrg"] == Decimal("467.00")


def test_non_brokered_fees_kept_separate_from_premium_split():
    payment = _payment(
        premium="500.00",
        tax="10.00",
        policy_fee="25.00",
    )
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    assert buckets["corgi_admin"] == Decimal("110.00")  # 22% of 500
    assert buckets["techrrg"] == Decimal("243.50")  # 46.7% of 500 + 10 tax
    assert buckets["corgire"] == Decimal("141.50")  # 28.3% of 500
    assert buckets["dane"] == Decimal("15.00")  # 3% of 500
    assert buckets["admin_fee"] == Decimal("25.00")  # policy_fee


def test_revenue_split_handles_missing_attributes_on_payment():
    # Bare object with only premium — other fields default to 0.
    payment = SimpleNamespace(amount=Decimal("100.00"))
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    assert buckets["corgi_admin"] == Decimal("22.00")
    assert buckets["techrrg"] == Decimal("46.70")
    assert buckets["corgire"] == Decimal("28.30")
    assert buckets["dane"] == Decimal("3.00")
    assert buckets["admin_fee"] == Decimal("0.00")


def test_revenue_split_returns_decimal_values_only():
    payment = _payment(premium="500.00", tax="5.00", policy_fee="1.00")
    policy = _policy(is_brokered=False)

    buckets = revenue_split(payment, policy)

    for key in ("corgi_admin", "techrrg", "corgire", "dane", "admin_fee"):
        assert key in buckets
        assert isinstance(buckets[key], Decimal)
