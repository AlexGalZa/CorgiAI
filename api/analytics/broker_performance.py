"""
Broker Performance Scoreboard Analytics (V3 #45)

Per producer/broker:
- Production volume (total premium written)
- Hit ratio (quotes submitted → policies bound)
- Average deal size
- Commission earned
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db.models import Count, Sum
from django.db.models.functions import Coalesce


def get_broker_performance() -> dict[str, Any]:
    """Build the broker performance scoreboard.

    Returns a dict with:
        ``brokers``: list of per-producer performance dicts.
        ``total_production``: float — total premium across all producers.
        ``total_commission``: float — total commission across all producers.
    """
    from producers.models import CommissionPayout, PolicyProducer, Producer
    from policies.models import Policy
    from quotes.models import Quote

    # Get all active producers
    producers = Producer.objects.filter(is_active=True).order_by("name")

    broker_rows = []

    for producer in producers:
        # Policies this producer is assigned to
        policy_assignments = PolicyProducer.objects.filter(producer=producer)
        policy_ids = list(policy_assignments.values_list("policy_id", flat=True))

        # Production volume: total premium on bound policies
        production = Decimal("0")
        bound_count = 0
        avg_deal_size = None

        if policy_ids:
            stats = Policy.objects.filter(
                id__in=policy_ids,
                status__in=["active", "expired"],
            ).aggregate(
                total_premium=Coalesce(Sum("premium"), Decimal("0")),
                count=Count("id"),
            )
            production = stats["total_premium"] or Decimal("0")
            bound_count = stats["count"] or 0
            avg_deal_size = float(production / bound_count) if bound_count > 0 else None

        # Quotes submitted via this producer's org (using ReferralPartner link if any)
        # We calculate hit ratio as: bound_count / total_quotes_in_same_org
        # A simpler approximation: bound policies / quotes from orgs that have this producer
        quote_count = 0
        if policy_ids:
            # Get unique org IDs from bound policies
            org_ids = list(
                Policy.objects.filter(id__in=policy_ids)
                .values_list("quote__organization_id", flat=True)
                .distinct()
            )
            if org_ids:
                quote_count = (
                    Quote.objects.filter(
                        organization_id__in=org_ids,
                        status__in=[
                            "submitted",
                            "needs_review",
                            "quoted",
                            "purchased",
                            "declined",
                        ],
                    )
                    .exclude(is_deleted=True)
                    .count()
                )

        hit_ratio = (
            round(bound_count / quote_count * 100, 1) if quote_count > 0 else None
        )

        # Commission earned (sum of all commission payouts)
        commission = CommissionPayout.objects.filter(
            producer=producer,
            status__in=["calculated", "approved", "paid"],
        ).aggregate(total=Coalesce(Sum("amount"), Decimal("0")))["total"]

        broker_rows.append(
            {
                "producer_id": producer.id,
                "producer_name": producer.name,
                "producer_type": producer.get_producer_type_display(),
                "production_volume": float(production),
                "quote_count": quote_count,
                "bound_count": bound_count,
                "hit_ratio": hit_ratio,
                "avg_deal_size": avg_deal_size,
                "commission_earned": float(commission),
            }
        )

    # Sort by production volume descending
    broker_rows.sort(key=lambda x: -x["production_volume"])

    total_production = sum(b["production_volume"] for b in broker_rows)
    total_commission = sum(b["commission_earned"] for b in broker_rows)

    return {
        "brokers": broker_rows,
        "total_production": total_production,
        "total_commission": total_commission,
    }
