from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "users"

    def ready(self):
        from auditlog.registry import auditlog
        from users.models import User, UserDocument

        auditlog.register(User)
        auditlog.register(UserDocument)
