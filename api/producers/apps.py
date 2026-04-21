from django.apps import AppConfig


class ProducersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "producers"

    def ready(self):
        from auditlog.registry import auditlog
        from producers.models import CommissionPayout, Producer, PolicyProducer

        auditlog.register(Producer)
        auditlog.register(PolicyProducer)
        auditlog.register(CommissionPayout)

        # Register signal handlers (commission reversal on policy cancellation, etc.)
        import producers.signals  # noqa: F401
