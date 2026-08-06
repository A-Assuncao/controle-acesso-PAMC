from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        # Conecta signals do admin (diff antes/depois)
        from . import admin_signals  # noqa: F401
