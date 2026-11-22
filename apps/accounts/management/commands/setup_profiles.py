from django.core.management.base import BaseCommand, CommandError

from apps.accounts.signals import setup_profiles


class Command(BaseCommand):
    help = "Sincroniza los perfiles con los permisos configurados."

    def handle(self, *args, **options):
        try:
            setup_profiles()
        except KeyError as exc:
            raise CommandError(f"Permiso inexistente: {exc}") from exc
        self.stdout.write(self.style.SUCCESS("Perfiles sincronizados."))
