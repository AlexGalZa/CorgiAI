from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organizations"

    def ready(self):
        from auditlog.registry import auditlog
        from organizations.models import Organization, OrganizationMember

        auditlog.register(Organization)
        auditlog.register(OrganizationMember)
