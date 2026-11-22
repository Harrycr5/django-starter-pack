from django.apps import AppConfig


class CommonConfig(AppConfig):
    name = "apps.common"

    def ready(self):
        from . import schema  # noqa: F401
