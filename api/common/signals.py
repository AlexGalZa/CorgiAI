"""
Django signals for cross-app notifications (Slack, etc.).

Hooks into:
- Quote status changes (quoted → notify Slack)
- Policy creation (policy bound → notify Slack)
- Claim creation (claim filed → notify Slack)
- Payment failures (tracked via Payment model)
- RefundRequest creation

Signals are connected in apps.py of each relevant app's AppConfig,
or in this module's ready() equivalent.

Connect by importing this module in your AppConfig.ready():
    from common import signals  # noqa
"""

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# ── Quote signals ─────────────────────────────────────────────────────────────


def connect_quote_signals():
    from quotes.models import Quote

    @receiver(post_save, sender=Quote, dispatch_uid="slack_quote_created")
    def on_quote_status_quoted(sender, instance: Quote, created: bool, **kwargs):
        """Notify Slack when a quote transitions to 'quoted' status."""
        # Only fire when status becomes 'quoted'
        if not created and instance.status == "quoted" and instance.quote_amount:
            try:
                from common.slack import SlackNotifier
                from common.constants import COVERAGE_DISPLAY_NAMES

                company_name = ""
                if instance.company:
                    company_name = instance.company.entity_legal_name or ""

                coverage_types = [
                    COVERAGE_DISPLAY_NAMES.get(c, c)
                    for c in (instance.coverage_selections or [])
                ]
                amount = (
                    f"${instance.quote_amount:,.2f}" if instance.quote_amount else "—"
                )

                SlackNotifier.quote_created(
                    quote_number=instance.quote_number or str(instance.pk),
                    company=company_name,
                    amount=amount,
                    coverage_types=coverage_types,
                )
            except Exception:
                logger.exception(
                    "Failed to send Slack notification for quote %s", instance.pk
                )


# ── Policy signals ────────────────────────────────────────────────────────────


def connect_policy_signals():
    from policies.models import Policy

    @receiver(post_save, sender=Policy, dispatch_uid="slack_policy_bound")
    def on_policy_created(sender, instance: Policy, created: bool, **kwargs):
        """Notify Slack when a new policy is created (bound)."""
        if created:
            try:
                from common.slack import SlackNotifier

                company_name = ""
                if instance.quote and instance.quote.company:
                    company_name = instance.quote.company.entity_legal_name or ""

                coverage_display = (
                    instance.coverage_type.replace("-", " ").title()
                    if instance.coverage_type
                    else "Insurance"
                )

                SlackNotifier.policy_bound(
                    policy_number=instance.policy_number,
                    company=company_name,
                    coverage_type=coverage_display,
                    premium=f"${instance.premium:,.2f}",
                )
            except Exception:
                logger.exception(
                    "Failed to send Slack notification for policy %s", instance.pk
                )


# ── Claim signals ─────────────────────────────────────────────────────────────


def connect_claim_signals():
    from claims.models import Claim

    @receiver(post_save, sender=Claim, dispatch_uid="slack_claim_filed")
    def on_claim_created(sender, instance: Claim, created: bool, **kwargs):
        """Notify Slack when a new claim is filed."""
        if created:
            try:
                from common.slack import SlackNotifier

                company_name = ""
                if hasattr(instance, "policy") and instance.policy:
                    policy = instance.policy
                    if policy.quote and policy.quote.company:
                        company_name = policy.quote.company.entity_legal_name or ""
                    coverage_display = (
                        policy.coverage_type.replace("-", " ").title()
                        if policy.coverage_type
                        else "Insurance"
                    )
                else:
                    coverage_display = "Unknown"

                description = getattr(instance, "description", "") or ""

                SlackNotifier.claim_filed(
                    claim_id=str(instance.pk),
                    company=company_name,
                    coverage_type=coverage_display,
                    description=description,
                )
            except Exception:
                logger.exception(
                    "Failed to send Slack notification for claim %s", instance.pk
                )


# ── Payment failure signals ───────────────────────────────────────────────────


def connect_payment_signals():
    from policies.models import Payment

    @receiver(post_save, sender=Payment, dispatch_uid="slack_payment_failed")
    def on_payment_status_change(sender, instance: Payment, created: bool, **kwargs):
        """Notify Slack when a payment is marked as failed."""
        if instance.status in ("failed", "payment_failed"):
            try:
                from common.slack import SlackNotifier

                policy = instance.policy
                company_name = ""
                if policy.quote and policy.quote.company:
                    company_name = policy.quote.company.entity_legal_name or ""

                SlackNotifier.payment_failed(
                    policy_number=policy.policy_number,
                    company=company_name,
                    amount=f"${instance.amount:,.2f}",
                )
            except Exception:
                logger.exception(
                    "Failed to send Slack notification for payment %s", instance.pk
                )


# ── Refund signals ────────────────────────────────────────────────────────────


def connect_refund_signals():
    from stripe_integration.models import RefundRequest

    @receiver(post_save, sender=RefundRequest, dispatch_uid="slack_refund_requested")
    def on_refund_request_created(
        sender, instance: RefundRequest, created: bool, **kwargs
    ):
        """Notify Slack when a new refund request is submitted."""
        if created:
            try:
                from common.slack import SlackNotifier

                SlackNotifier.refund_requested(
                    refund_id=instance.pk,
                    policy_number=instance.policy.policy_number,
                    amount=f"${instance.amount:,.2f}",
                    reason=instance.get_reason_display(),
                )
            except Exception:
                logger.exception(
                    "Failed to send Slack notification for refund request %s",
                    instance.pk,
                )


def connect_audit_signals():
    """
    Wire post_save / post_delete signals on key models to AuditLogEntry.

    Models audited: Quote, Policy, Claim, Payment, Company, User
    """
    from django.db.models.signals import post_save, post_delete

    # Lazy imports inside function to avoid app-loading issues.
    def _get_models():
        from quotes.models import Quote, Company
        from policies.models import Policy
        from claims.models import Claim
        from users.models import User

        return [
            (Quote, "Quote"),
            (Policy, "Policy"),
            (Claim, "Claim"),
            (Company, "Company"),
            (User, "User"),
        ]

    def make_save_handler(model_label):
        def on_save(sender, instance, created, **kwargs):
            try:
                from common.models import AuditLogEntry

                AuditLogEntry.objects.create(
                    user=None,  # system signal — no request context
                    action="create" if created else "update",
                    model_name=model_label,
                    object_id=str(instance.pk),
                    changes={},
                )
            except Exception:
                logger.exception(
                    "Failed to write AuditLogEntry for %s %s", model_label, instance.pk
                )

        return on_save

    def make_delete_handler(model_label):
        def on_delete(sender, instance, **kwargs):
            try:
                from common.models import AuditLogEntry

                AuditLogEntry.objects.create(
                    user=None,
                    action="delete",
                    model_name=model_label,
                    object_id=str(instance.pk),
                    changes={},
                )
            except Exception:
                logger.exception(
                    "Failed to write AuditLogEntry for delete %s %s",
                    model_label,
                    instance.pk,
                )

        return on_delete

    for model_cls, label in _get_models():
        post_save.connect(
            make_save_handler(label),
            sender=model_cls,
            dispatch_uid=f"audit_save_{label.lower()}",
            weak=False,
        )
        post_delete.connect(
            make_delete_handler(label),
            sender=model_cls,
            dispatch_uid=f"audit_delete_{label.lower()}",
            weak=False,
        )


def connect_all_signals():
    """Connect all signal handlers. Call from AppConfig.ready()."""
    connect_quote_signals()
    connect_policy_signals()
    connect_claim_signals()
    connect_payment_signals()
    connect_refund_signals()
    connect_audit_signals()
