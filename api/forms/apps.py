"""Django app configuration for the forms module."""

from django.apps import AppConfig


class FormsConfig(AppConfig):
    """App config for the Form Builder."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "forms"
    verbose_name = "Form Builder"
