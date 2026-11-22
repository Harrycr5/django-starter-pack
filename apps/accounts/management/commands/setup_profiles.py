import logging

from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, DatabaseError

from apps.accounts.profile_sync import ProfileConfigurationError, sync_profiles

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sincroniza los perfiles con los permisos configurados."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Muestra los cambios sin escribir en la base.")
        parser.add_argument("--database", default=DEFAULT_DB_ALIAS, help="Alias de la base de datos.")

    def handle(self, *args, **options):
        using = options["database"]
        dry_run = options["dry_run"]
        try:
            changes = sync_profiles(using=using, dry_run=dry_run)
        except (ProfileConfigurationError, DatabaseError) as exc:
            logger.error("Falló la sincronización en %s (simulación=%s): %s", using, dry_run, type(exc).__name__)
            message = str(exc) if isinstance(exc, ProfileConfigurationError) else "Comprueba la conexión y las migraciones."
            raise CommandError(f"No se pudieron sincronizar los perfiles en {using}. {message}") from exc

        for change in changes:
            action = "sin cambios"
            if change["created"]:
                action = "crear grupo" if dry_run else "grupo creado"
            elif change["added"] or change["removed"]:
                action = "actualizar" if dry_run else "grupo actualizado"
            self.stdout.write(f"{change['profile']} ({action})")
            for key in change["added"]:
                self.stdout.write(f"  + {key}")
            for key in change["removed"]:
                self.stdout.write(f"  - {key}")
        if dry_run:
            self.stdout.write(self.style.WARNING("Simulación completada sin escrituras."))
        else:
            self.stdout.write(self.style.SUCCESS("Perfiles sincronizados."))
