from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from quotes.models import Quote


@dataclass
class CreatePaymentLinkInput:
    quote: Quote
    billing_frequency: str = "annual"
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    effective_date: Optional[date] = None
    coverages: Optional[list[str]] = field(default=None)
