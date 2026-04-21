from django.apps import AppConfig


class ClaimsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "claims"

    def ready(self):
        from auditlog.registry import auditlog
        from claims.models import Claim

        auditlog.register(Claim)
