from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List


class ProrationBehavior(str, Enum):
    CREATE_PRORATIONS = "create_prorations"
    NONE = "none"
    ALWAYS_INVOICE = "always_invoice"


@dataclass
class GetOrCreateCustomerInput:
    email: str
    name: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class LineItemInput:
    name: str
    amount_cents: int
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateProductInput:
    name: str
    metadata: Optional[Dict[str, Any]] = None
    # When True, StripeService.create_product will stamp ``brokered=true``
    # into the Stripe Product metadata (matching how we already tag
    # ``carrier``). Used by the BROKERED product variants flow (Trello 1.1).
    brokered: bool = False


@dataclass
class CreateRecurringPriceInput:
    product_id: str
    unit_amount: int
    currency: str = "usd"
    interval: str = "month"
    interval_count: int = 1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateOneTimeCheckoutInput:
    customer_id: str
    amount_cents: int
    product_name: str
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, Any]] = None
    product_metadata: Optional[Dict[str, Any]] = None
    promotion_code_id: Optional[str] = None


@dataclass
class CreateMultiLineCheckoutInput:
    customer_id: str
    line_items: List[dict]
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateSubscriptionCheckoutInput:
    customer_id: str
    amount_cents: int
    product_name: str
    success_url: str
    cancel_url: str
    interval: str = "month"
    interval_count: int = 1
    metadata: Optional[Dict[str, Any]] = None
    product_metadata: Optional[Dict[str, Any]] = None
    price_metadata: Optional[Dict[str, Any]] = None
    subscription_metadata: Optional[Dict[str, Any]] = None
    promotion_code_id: Optional[str] = None
    trial_end: Optional[int] = None


@dataclass
class RecurringLineItemInput:
    name: str
    amount_cents: int
    interval: str = "month"
    interval_count: int = 1
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class CreateMultiLineSubscriptionCheckoutInput:
    customer_id: str
    line_items: List[RecurringLineItemInput]
    success_url: str
    cancel_url: str
    metadata: Optional[Dict[str, Any]] = None
    subscription_metadata: Optional[Dict[str, Any]] = None
    trial_end: Optional[int] = None
    promotion_code_id: Optional[str] = None


@dataclass
class CreateDirectSubscriptionInput:
    customer_id: str
    line_items: List[RecurringLineItemInput]
    billing_cycle_anchor: int
    subscription_metadata: Optional[Dict[str, Any]] = None
