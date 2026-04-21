"""Django app configuration for the admin_api module."""

from django.apps import AppConfig


class AdminApiConfig(AppConfig):
    """App config for the Admin API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "admin_api"
    verbose_name = "Admin API"
