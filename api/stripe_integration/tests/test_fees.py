"""
Unit tests for stripe_integration.fees.calculate_fees.

Covers:
  * Card processor fee formula (2.9% + $0.30)
  * ACH processor fee with the $5.00 cap
  * State tax routing (known / unknown / None state codes)
  * Defensive behavior on zero / negative amounts
"""

import pytest

from stripe_integration.fees import (
    ACH_CAP_CENTS,
    CARD_FIXED_FEE_CENTS,
    STATE_TAX_RATES,
    calculate_fees,
)


# ── Card processor fees ─────────────────────────────────────────────


def test_card_fee_on_ten_dollars():
    # 2.9% of $10 (1000c) = 29c, + 30c fixed = 59c
    result = calculate_fees(1000, payment_method="card")
    assert result["processor_fee_cents"] == 59
    assert result["tax_cents"] == 0
    assert result["total_cents"] == 59


def test_card_fee_on_one_hundred_dollars():
    # 2.9% of $100 (10000c) = 290c, + 30c fixed = 320c
    result = calculate_fees(10000, payment_method="card")
    assert result["processor_fee_cents"] == 320


def test_card_is_the_default_payment_method():
    # No payment_method arg → card.
    assert calculate_fees(1000) == calculate_fees(1000, payment_method="card")


def test_unknown_payment_method_defaults_to_card():
    # Defensive branch: bitcoin / apple_pay / whatever → card rates.
    result_unknown = calculate_fees(10000, payment_method="bitcoin")
    result_card = calculate_fees(10000, payment_method="card")
    assert result_unknown == result_card


def test_card_fee_handles_zero_amount():
    # 0 * 2.9% + 30c fixed = 30c
    result = calculate_fees(0, payment_method="card")
    assert result["processor_fee_cents"] == CARD_FIXED_FEE_CENTS
    assert result["total_cents"] == CARD_FIXED_FEE_CENTS


# ── ACH processor fees ──────────────────────────────────────────────


def test_ach_fee_below_cap():
    # 0.8% of $100 (10000c) = 80c, well below 500c cap.
    result = calculate_fees(10000, payment_method="ach")
    assert result["processor_fee_cents"] == 80


def test_ach_fee_hits_cap_at_large_amounts():
    # 0.8% of $10,000 (1,000,000c) = 8000c → capped at 500c.
    result = calculate_fees(1_000_000, payment_method="ach")
    assert result["processor_fee_cents"] == ACH_CAP_CENTS
    assert ACH_CAP_CENTS == 500


def test_ach_fee_at_cap_boundary():
    # 500c / 0.008 = 62500c = $625 → everything above pays the cap.
    at_boundary = calculate_fees(62_500, payment_method="ach")
    assert at_boundary["processor_fee_cents"] == 500

    above_boundary = calculate_fees(70_000, payment_method="ach")
    assert above_boundary["processor_fee_cents"] == 500


def test_ach_payment_method_is_case_insensitive():
    lower = calculate_fees(10000, payment_method="ach")
    upper = calculate_fees(10000, payment_method="ACH")
    mixed = calculate_fees(10000, payment_method="Ach")
    assert lower == upper == mixed


# ── State tax routing ──────────────────────────────────────────────


def test_known_state_with_zero_tax_rate():
    # Placeholder rates are 0% until legal confirms — verify the code path
    # without hard-coding a specific rate value.
    result = calculate_fees(10000, payment_method="card", state="CA")
    expected_rate = STATE_TAX_RATES["CA"]
    assert result["tax_cents"] == int(round(10000 * expected_rate))


def test_unknown_state_yields_zero_tax():
    result = calculate_fees(10000, payment_method="card", state="ZZ")
    assert result["tax_cents"] == 0


def test_none_state_yields_zero_tax():
    result = calculate_fees(10000, payment_method="card", state=None)
    assert result["tax_cents"] == 0


def test_state_code_is_uppercased_before_lookup():
    # Known state code given in lowercase must still route correctly.
    lower = calculate_fees(10000, payment_method="card", state="ca")
    upper = calculate_fees(10000, payment_method="card", state="CA")
    assert lower == upper


def test_tax_with_nonzero_rate_is_added_to_total(monkeypatch):
    # Monkeypatch a nonzero rate for NY to exercise the tax math once legal
    # fills in the real numbers — keeps the assertion honest today without
    # binding to a specific legal value.
    monkeypatch.setitem(STATE_TAX_RATES, "NY", 0.10)

    result = calculate_fees(10000, payment_method="card", state="NY")
    # 2.9% of 10000 = 290 + 30 fixed = 320 processor
    # 10% tax of 10000 = 1000 tax
    assert result["processor_fee_cents"] == 320
    assert result["tax_cents"] == 1000
    assert result["total_cents"] == 1320


# ── Defensive behavior ─────────────────────────────────────────────


def test_negative_amount_raises_value_error():
    with pytest.raises(ValueError):
        calculate_fees(-1, payment_method="card")


def test_total_is_processor_fee_plus_tax():
    result = calculate_fees(10000, payment_method="card", state="CA")
    assert result["total_cents"] == result["processor_fee_cents"] + result["tax_cents"]


def test_returned_values_are_integers():
    result = calculate_fees(1234, payment_method="card", state="CA")
    for key in ("processor_fee_cents", "tax_cents", "total_cents"):
        assert isinstance(result[key], int), (
            f"{key} must be int, got {type(result[key])}"
        )
