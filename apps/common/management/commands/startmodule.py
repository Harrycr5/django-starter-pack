import keyword
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Crea un paquete en apps/ con su configuracion y su URLconf."

    def add_arguments(self, parser):
        parser.add_argument("name")

    def handle(self, *args, **options):
        name = options["name"]
        if not name.isascii() or not name.isidentifier() or name.startswith("_") or keyword.iskeyword(name):
            raise CommandError("Usa un identificador Python ASCII sin guion inicial.")

        apps_dir = Path(__file__).resolve().parents[3]
        target = apps_dir / name
        try:
            target.mkdir()
        except FileExistsError as exc:
            raise CommandError(f"El paquete apps.{name} ya existe.") from exc
        (target / "__init__.py").touch()
        (target / "apps.py").write_text(
            'from django.apps import AppConfig\n\n\n'
            f'class ModuleConfig(AppConfig):\n    name = "apps.{name}"\n',
            encoding="utf-8",
        )
        (target / "urls.py").write_text("urlpatterns = []\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Paquete creado en apps/{name}/."))
