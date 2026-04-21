"""
Webhook models — re-exported from delivery.py for Django app registration.
"""

from webhooks.delivery import WebhookEndpoint, WebhookDelivery  # noqa: F401

__all__ = ["WebhookEndpoint", "WebhookDelivery"]
