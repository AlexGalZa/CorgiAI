"""
Processor fee and tax calculation for brokered policies.

Passes Stripe processing fees (2.9% + $0.30 for card, 0.8% capped at $5.00
for ACH) through to the customer at checkout. Tax rates are tracked per
US state; the initial set is a placeholder until legal confirms the final
rates.

All amounts are handled in integer cents to avoid floating-point drift.
The returned breakdown is intended to be attached to Stripe Checkout
sessions as additional line items when the caller flags the policy as
brokered.
"""

from __future__ import annotations

from typing import Optional, Dict


# Card: 2.9% + $0.30 per transaction
CARD_PERCENT_RATE = 0.029
CARD_FIXED_FEE_CENTS = 30

# ACH: 0.8% capped at $5.00
ACH_PERCENT_RATE = 0.008
ACH_CAP_CENTS = 500

# State tax placeholders — legal to confirm final rates.
# Values are percent (e.g. 0.0725 == 7.25%).
STATE_TAX_RATES: Dict[str, float] = {
    "CA": 0.0,
    "TX": 0.0,
    "NY": 0.0,
}


def calculate_fees(
    amount_cents: int,
    payment_method: str = "card",
    state: Optional[str] = None,
) -> dict:
    """Calculate processor fees and tax for a brokered-policy checkout.

    Args:
        amount_cents: Pre-fee premium amount in cents.
        payment_method: ``'card'`` or ``'ach'``. Defaults to ``'card'``.
        state: Two-letter US state code. Unknown / ``None`` -> 0% tax.

    Returns:
        Dict with ``processor_fee_cents``, ``tax_cents``, ``total_cents``
        (total excluding the base ``amount_cents`` — it is the amount
        added on top of the premium).
    """
    if amount_cents < 0:
        raise ValueError("amount_cents must be non-negative")

    method = (payment_method or "card").lower()

    if method == "ach":
        processor_fee_cents = min(
            int(round(amount_cents * ACH_PERCENT_RATE)),
            ACH_CAP_CENTS,
        )
    else:
        # Default to card for unknown methods
        processor_fee_cents = (
            int(round(amount_cents * CARD_PERCENT_RATE)) + CARD_FIXED_FEE_CENTS
        )

    tax_rate = 0.0
    if state:
        tax_rate = STATE_TAX_RATES.get(state.upper(), 0.0)
    tax_cents = int(round(amount_cents * tax_rate))

    total_cents = processor_fee_cents + tax_cents

    return {
        "processor_fee_cents": processor_fee_cents,
        "tax_cents": tax_cents,
        "total_cents": total_cents,
    }
