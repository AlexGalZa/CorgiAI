from django.apps import AppConfig


class StripeIntegrationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "stripe_integration"

    def ready(self):
        from auditlog.registry import auditlog
        from stripe_integration.models import RefundRequest

        auditlog.register(RefundRequest)
