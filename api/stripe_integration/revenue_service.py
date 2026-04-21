"""
Revenue recognition service for the Corgi Insurance platform.

Codifies the payout-split flow chart that Emily/Scott have historically
executed by hand each month:

- Brokered policy (``policy.is_brokered`` True):
    100% of premium routes to the Corgi Admin bucket. The external
    carrier has already been paid at bind time, so Corgi only needs to
    recognize the brokerage fee it retained.

- Non-brokered policy:
    The retained premium is split across four buckets:
        * Corgi Admin : 22.0%
        * TechRRG     : 46.7% (plus any tax collected on the transaction)
        * CorgiRe     : 28.3%
        * Dane        :  3.0%

In both cases, policy fees / admin fees / taxes that were collected on
top of the premium are routed to a dedicated ``admin_fee`` bucket so
downstream reconciliation can tell premium dollars from fee dollars.

Treasury (Mercury / Meow) wire routing is intentionally stubbed in this
initial revision. Each bucket logs a "would send $X to <account>" line
so finance can verify the numbers before wires go live. Actual wire
integration is a follow-up task.
"""

import logging
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


# Non-brokered split percentages. These are the canonical rates from the
# revenue flow chart — change here if finance updates the agreement.
CORGI_ADMIN_RATE = Decimal("0.220")
TECHRRG_RATE = Decimal("0.467")
CORGIRE_RATE = Decimal("0.283")
DANE_RATE = Decimal("0.030")

# Logical "account" identifiers used by the treasury stub. The real
# Mercury/Meow account IDs will be wired in via settings once the wire
# integration lands.
_TREASURY_ACCOUNTS = {
    "corgi_admin": "mercury:corgi-admin",
    "techrrg": "mercury:techrrg-operating",
    "corgire": "meow:corgire-reserve",
    "dane": "mercury:dane-payouts",
    "admin_fee": "mercury:corgi-admin-fees",
}

_TWO_PLACES = Decimal("0.01")


def _q(value: Decimal) -> Decimal:
    """Quantize to 2 decimal places using banker-safe HALF_UP rounding."""
    return Decimal(value).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)


def _collected_fees(payment) -> Decimal:
    """Pull any policy/admin fees or taxes recorded on the transaction.

    ``payment`` may be a ``PolicyTransaction`` or anything exposing the
    same accounting attributes (taxes, policy_fee_delta, membership_fee_delta,
    admin_fee_amount). Missing attributes are treated as zero so callers
    can pass lightweight stand-ins from tests or from one-off scripts.
    """
    total = Decimal("0")
    for attr in (
        "policy_fee_delta",
        "membership_fee_delta",
        "admin_fee_amount",
    ):
        total += Decimal(getattr(payment, attr, 0) or 0)
    return total


def _premium_amount(payment) -> Decimal:
    """Pull the premium dollars that should be split across buckets."""
    for attr in ("gross_written_premium", "amount", "premium"):
        value = getattr(payment, attr, None)
        if value is not None:
            return Decimal(value)
    return Decimal("0")


def _tax_amount(payment) -> Decimal:
    return Decimal(getattr(payment, "tax_amount", 0) or 0)


def revenue_split(payment, policy) -> dict:
    """Compute the bucket-level split for a single premium event.

    Args:
        payment: A ``PolicyTransaction`` (or compatible object) carrying
            the premium / tax / fee amounts that were collected.
        policy: The ``Policy`` the payment belongs to. ``policy.is_brokered``
            toggles between the 100%-to-admin brokered flow and the
            22 / 46.7 / 28.3 / 3 non-brokered split.

    Returns:
        A dict with Decimal values for keys:
            ``corgi_admin``, ``techrrg``, ``corgire``, ``dane``, ``admin_fee``
    """
    premium = _premium_amount(payment)
    tax = _tax_amount(payment)
    fees = _collected_fees(payment)

    if getattr(policy, "is_brokered", False):
        buckets = {
            "corgi_admin": _q(premium),
            "techrrg": Decimal("0.00"),
            "corgire": Decimal("0.00"),
            "dane": Decimal("0.00"),
            "admin_fee": _q(fees + tax),
        }
    else:
        buckets = {
            "corgi_admin": _q(premium * CORGI_ADMIN_RATE),
            "techrrg": _q(premium * TECHRRG_RATE + tax),
            "corgire": _q(premium * CORGIRE_RATE),
            "dane": _q(premium * DANE_RATE),
            "admin_fee": _q(fees),
        }

    _stub_treasury_routing(buckets, policy)
    return buckets


def _stub_treasury_routing(buckets: dict, policy) -> None:
    """Log the wire transfers that *would* be executed.

    Real Mercury/Meow wire integration is a follow-up card. Until that
    lands, every split run emits one log line per bucket so finance can
    double-check amounts against the monthly flow chart.
    """
    policy_ref = getattr(policy, "policy_number", None) or getattr(policy, "pk", "?")
    for bucket, amount in buckets.items():
        if amount <= 0:
            continue
        account = _TREASURY_ACCOUNTS.get(bucket, bucket)
        logger.info(
            "Treasury routing not implemented: would send $%s to %s (policy=%s, bucket=%s)",
            amount,
            account,
            policy_ref,
            bucket,
        )
