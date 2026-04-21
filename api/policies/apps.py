from django.apps import AppConfig


class PoliciesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "policies"

    def ready(self):
        from auditlog.registry import auditlog
        from policies.models import Policy, Payment, PolicyTransaction

        auditlog.register(Policy)
        auditlog.register(Payment)
        auditlog.register(PolicyTransaction)
