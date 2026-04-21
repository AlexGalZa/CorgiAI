from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "common"

    def ready(self):
        # Connect Slack notification signals for key platform events
        try:
            from common.signals import connect_all_signals

            connect_all_signals()
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Failed to connect common signals")

        # Wire up model cache invalidation signals
        try:
            from common.cache import setup_model_cache_invalidations

            setup_model_cache_invalidations()
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Failed to wire model cache invalidations"
            )
