"""
SLA service functions for starting, completing, and checking SLA metrics.
"""

from decimal import Decimal
from django.utils import timezone

from sla.models import SLAMetric


def start_sla(
    metric_type: str,
    entity_type: str,
    entity_id: int,
    target_hours: float | None = None,
) -> SLAMetric:
    """
    Start an SLA clock for the given entity.
    If target_hours is not provided, uses the default for the metric_type.
    """
    if target_hours is None:
        target_hours = SLAMetric.DEFAULT_TARGET_HOURS.get(metric_type, 24)

    sla = SLAMetric.objects.create(
        metric_type=metric_type,
        entity_type=entity_type,
        entity_id=entity_id,
        target_hours=Decimal(str(target_hours)),
        started_at=timezone.now(),
    )
    return sla


def complete_sla(
    metric_type: str, entity_type: str, entity_id: int
) -> SLAMetric | None:
    """
    Mark an SLA as completed. Updates breached status based on elapsed time.
    Returns None if no open SLA found for this entity.
    """
    sla = SLAMetric.objects.filter(
        metric_type=metric_type,
        entity_type=entity_type,
        entity_id=entity_id,
        completed_at__isnull=True,
    ).first()

    if not sla:
        return None

    sla.completed_at = timezone.now()
    elapsed_hours = (sla.completed_at - sla.started_at).total_seconds() / 3600
    sla.breached = elapsed_hours > float(sla.target_hours)
    sla.save(update_fields=["completed_at", "breached", "updated_at"])
    return sla


def get_compliance_rate(metric_type: str | None = None) -> dict:
    """
    Calculate SLA compliance rate across all completed SLAs.
    Returns dict with total, breached, compliant, compliance_pct.
    """
    qs = SLAMetric.objects.filter(completed_at__isnull=False)
    if metric_type:
        qs = qs.filter(metric_type=metric_type)

    total = qs.count()
    breached = qs.filter(breached=True).count()
    compliant = total - breached
    pct = round((compliant / total * 100), 1) if total > 0 else 100.0

    return {
        "total": total,
        "breached": breached,
        "compliant": compliant,
        "compliance_pct": pct,
    }
