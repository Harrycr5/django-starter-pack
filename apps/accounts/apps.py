from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountsConfig(AppConfig):
    name = "apps.accounts"

    def ready(self):
        from .signals import sync_profiles

        # Run after Django creates permissions for the last app with models.
        post_migrate.connect(sync_profiles, dispatch_uid="accounts.sync_profiles")
