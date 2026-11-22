from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier

import pytest
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, connections
from django.db.models.signals import m2m_changed
from django.test.utils import CaptureQueriesContext

from apps.accounts.profile_sync import ProfileConfigurationError, sync_profiles
from apps.accounts.profiles import ADMIN_PROFILE, DEFAULT_PROFILE

pytestmark = pytest.mark.django_db


def test_sync_after_migrations_includes_permissions_from_new_modules():
    assert not Group.objects.filter(name__in=[ADMIN_PROFILE, DEFAULT_PROFILE]).exists()
    content_type = ContentType.objects.create(app_label="new_module", model="document")
    permission = Permission.objects.create(content_type=content_type, codename="view_document", name="View document")

    sync_profiles()

    assert Group.objects.get(name=ADMIN_PROFILE).permissions.filter(pk=permission.pk).exists()
    assert not Group.objects.get(name=DEFAULT_PROFILE).permissions.filter(pk=permission.pk).exists()


def test_sync_is_idempotent_without_permission_writes(system_profiles):
    with CaptureQueriesContext(connection) as queries:
        changes = sync_profiles()

    assert all(not (change["created"] or change["added"] or change["removed"]) for change in changes)
    assert not any(query["sql"].startswith(("INSERT", "UPDATE", "DELETE")) for query in queries)


def test_sync_revokes_obsolete_permissions_and_preserves_custom_groups(system_profiles):
    obsolete = Permission.objects.get(content_type__app_label="accounts", codename="delete_user")
    default = Group.objects.get(name=DEFAULT_PROFILE)
    custom = Group.objects.create(name="Soporte")
    default.permissions.add(obsolete)
    custom.permissions.add(obsolete)

    changes = {change["profile"]: change for change in sync_profiles()}

    assert changes[DEFAULT_PROFILE]["removed"] == ["accounts.delete_user"]
    assert not default.permissions.filter(pk=obsolete.pk).exists()
    assert list(custom.permissions.all()) == [obsolete]


def test_dry_run_reports_creation_and_removal_without_writes(system_profiles):
    Group.objects.filter(name=ADMIN_PROFILE).delete()
    default = Group.objects.get(name=DEFAULT_PROFILE)
    obsolete = Permission.objects.get(content_type__app_label="accounts", codename="delete_user")
    default.permissions.add(obsolete)
    output = StringIO()

    with CaptureQueriesContext(connection) as queries:
        call_command("setup_profiles", "--database=default", "--dry-run", stdout=output)

    assert "Administrador (crear grupo)" in output.getvalue()
    assert "+ accounts.view_user" in output.getvalue()
    assert "- accounts.delete_user" in output.getvalue()
    assert not Group.objects.filter(name=ADMIN_PROFILE).exists()
    assert default.permissions.filter(pk=obsolete.pk).exists()
    assert not any(query["sql"].startswith(("INSERT", "UPDATE", "DELETE")) for query in queries)


def test_invalid_permissions_leave_database_untouched(settings):
    settings.PROFILE_PERMISSIONS = {DEFAULT_PROFILE: ("accounts.nonexistent",)}
    with pytest.raises(CommandError, match="accounts.nonexistent"):
        call_command("setup_profiles")
    assert not Group.objects.exists()


def test_sync_rolls_back_earlier_changes_on_write_failure():
    membership = Group.permissions.through

    def fail_when_setting_default(sender, instance, action, **kwargs):
        if instance.name == DEFAULT_PROFILE and action == "pre_add":
            raise RuntimeError("Fallo simulado")

    m2m_changed.connect(fail_when_setting_default, sender=membership)
    try:
        with pytest.raises(RuntimeError, match="Fallo simulado"):
            sync_profiles()
    finally:
        m2m_changed.disconnect(fail_when_setting_default, sender=membership)

    assert not Group.objects.exists()
    assert not membership.objects.exists()


def test_unknown_database_alias():
    with pytest.raises(CommandError, match="Alias de base de datos desconocido"):
        call_command("setup_profiles", "--database=unknown")


def test_router_can_reject_sync(monkeypatch):
    monkeypatch.setattr("apps.accounts.profile_sync.router.allow_migrate_model", lambda alias, model: model is not Group)
    with pytest.raises(ProfileConfigurationError, match="router"):
        sync_profiles()
    assert not Group.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_sync_creates_each_group_once():
    start = Barrier(2)

    def run():
        try:
            start.wait(timeout=10)
            return sync_profiles()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]

    assert sum(change["created"] for result in results for change in result) == 2
    assert Group.objects.get(name=ADMIN_PROFILE).permissions.count() == Permission.objects.count()
    assert Group.objects.get(name=DEFAULT_PROFILE).permissions.count() == 2
