from django.apps import AppConfig


class HubspotSyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "hubspot_sync"
    verbose_name = "HubSpot Sync"
