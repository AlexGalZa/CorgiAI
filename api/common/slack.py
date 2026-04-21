"""
Slack notification service for the Corgi Insurance platform.

Sends webhook POSTs to SLACK_WEBHOOK_URL (configured in Django settings).
Falls back gracefully if no webhook URL is configured.

Usage:
    from common.slack import SlackNotifier

    SlackNotifier.send("New quote submitted", details={
        "quote_number": "Q-12345",
        "company": "Acme Corp",
        "amount": "$1,234.56",
    })
"""

import logging
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SlackNotifier:
    """
    Simple Slack incoming webhook notifier.

    Sends structured messages with optional details fields.
    Silently no-ops if SLACK_WEBHOOK_URL is not configured.
    """

    EMOJI_MAP = {
        "quote_created": ":clipboard:",
        "policy_bound": ":white_check_mark:",
        "claim_filed": ":rotating_light:",
        "payment_failed": ":warning:",
        "refund_requested": ":money_with_wings:",
        "renewal_offered": ":calendar:",
        "default": ":bell:",
    }

    @staticmethod
    def _get_webhook_url() -> Optional[str]:
        return getattr(settings, "SLACK_WEBHOOK_URL", None)

    @staticmethod
    def send(
        event_type: str,
        title: str,
        details: Optional[dict] = None,
        color: str = "#ff5c00",
    ) -> bool:
        """
        Send a Slack notification.

        Args:
            event_type: Key used to pick an emoji (e.g. "quote_created")
            title: Main message text
            details: Optional dict of key-value pairs shown as attachment fields
            color: Sidebar color hex (default: Corgi orange)

        Returns:
            True if sent successfully, False otherwise.
        """
        webhook_url = SlackNotifier._get_webhook_url()
        if not webhook_url:
            logger.debug(
                "SLACK_WEBHOOK_URL not configured — skipping Slack notification"
            )
            return False

        emoji = SlackNotifier.EMOJI_MAP.get(
            event_type, SlackNotifier.EMOJI_MAP["default"]
        )
        env = getattr(settings, "ENVIRONMENT", "production")
        env_prefix = f"[{env.upper()}] " if env != "production" else ""

        payload: dict = {
            "attachments": [
                {
                    "color": color,
                    "fallback": f"{env_prefix}{emoji} {title}",
                    "pretext": f"{env_prefix}{emoji} *{title}*",
                    "mrkdwn_in": ["pretext", "fields"],
                }
            ]
        }

        if details:
            fields = []
            for key, value in details.items():
                fields.append(
                    {
                        "title": key,
                        "value": str(value) if value is not None else "—",
                        "short": True,
                    }
                )
            payload["attachments"][0]["fields"] = fields

        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=5,
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            logger.warning("Failed to send Slack notification: %s", e)
            return False

    # ── Convenience methods ───────────────────────────────────────────────────

    @staticmethod
    def quote_created(
        quote_number: str, company: str, amount: str, coverage_types: list[str]
    ):
        SlackNotifier.send(
            event_type="quote_created",
            title="New Quote Submitted",
            details={
                "Quote #": quote_number,
                "Company": company,
                "Amount": amount,
                "Coverages": ", ".join(coverage_types) if coverage_types else "—",
            },
        )

    @staticmethod
    def policy_bound(
        policy_number: str, company: str, coverage_type: str, premium: str
    ):
        SlackNotifier.send(
            event_type="policy_bound",
            title="Policy Bound 🎉",
            details={
                "Policy #": policy_number,
                "Company": company,
                "Coverage": coverage_type,
                "Premium": premium,
            },
            color="#10b981",
        )

    @staticmethod
    def claim_filed(claim_id: str, company: str, coverage_type: str, description: str):
        SlackNotifier.send(
            event_type="claim_filed",
            title="Claim Filed",
            details={
                "Claim #": claim_id,
                "Company": company,
                "Coverage": coverage_type,
                "Description": description[:200] if description else "—",
            },
            color="#ef4444",
        )

    @staticmethod
    def payment_failed(policy_number: str, company: str, amount: str):
        SlackNotifier.send(
            event_type="payment_failed",
            title="Payment Failed",
            details={
                "Policy #": policy_number,
                "Company": company,
                "Amount": amount,
            },
            color="#f59e0b",
        )

    @staticmethod
    def refund_requested(refund_id: int, policy_number: str, amount: str, reason: str):
        SlackNotifier.send(
            event_type="refund_requested",
            title="Refund Request Submitted",
            details={
                "Refund #": str(refund_id),
                "Policy #": policy_number,
                "Amount": amount,
                "Reason": reason,
            },
            color="#8b5cf6",
        )
