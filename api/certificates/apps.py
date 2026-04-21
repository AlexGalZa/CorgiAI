from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "certificates"

    def ready(self):
        from auditlog.registry import auditlog
        from certificates.models import CustomCertificate, AdditionalInsured

        auditlog.register(CustomCertificate)
        auditlog.register(AdditionalInsured)
