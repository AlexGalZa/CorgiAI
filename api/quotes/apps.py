from django.apps import AppConfig


class QuotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "quotes"

    def ready(self):
        from auditlog.registry import auditlog
        from quotes.models import Quote, CustomProduct

        auditlog.register(Quote)
        auditlog.register(CustomProduct)
