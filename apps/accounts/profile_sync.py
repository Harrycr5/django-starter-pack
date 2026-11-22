import logging

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import DEFAULT_DB_ALIAS, connections, router, transaction

from .profiles import ADMIN_PROFILE, DEFAULT_PROFILE, normalize_profile_name

logger = logging.getLogger(__name__)


class ProfileConfigurationError(Exception):
    pass


def sync_profiles(*, using=DEFAULT_DB_ALIAS, dry_run=False):
    if using not in connections:
        raise ProfileConfigurationError(f"Alias de base de datos desconocido: {using}")

    membership = Group.permissions.through
    if not all(router.allow_migrate_model(using, model) for model in (Group, Permission, ContentType, membership)):
        raise ProfileConfigurationError(f"El router impide sincronizar los perfiles en {using}.")

    with transaction.atomic(using=using):
        changes = _sync_profiles(using, dry_run)
        transaction.on_commit(
            lambda: logger.info("Perfiles sincronizados en %s (simulación=%s): %s", using, dry_run, changes),
            using=using,
        )
    return changes


def _sync_profiles(using, dry_run):
    permissions = Permission.objects.using(using).select_related("content_type").in_bulk()
    permission_keys = {pk: f"{permission.content_type.app_label}.{permission.codename}" for pk, permission in permissions.items()}
    available = set(permission_keys.values())
    configured = {name: set(keys) for name, keys in settings.PROFILE_PERMISSIONS.items()}
    configured[ADMIN_PROFILE] = available
    normalized = set()
    for name, keys in configured.items():
        key = normalize_profile_name(name)
        if not key or key in normalized:
            raise ProfileConfigurationError(f"Nombre de perfil vacío o duplicado: {name!r}")
        normalized.add(key)
        missing = keys - available
        if missing:
            raise ProfileConfigurationError(f"Permisos inexistentes para {name}: {', '.join(sorted(missing))}")

    groups = Group.objects.using(using)
    links = Group.permissions.through.objects.using(using)
    changes = []
    # Acquire locks in the same order across concurrent runs.
    for name, keys in sorted(configured.items()):
        if dry_run:
            group = groups.filter(name=name).first()
            created = group is None
        else:
            group, created = groups.select_for_update().get_or_create(name=name)

        current = set(links.filter(group=group).values_list("permission_id", flat=True)) if group else set()
        desired = {pk for pk, key in permission_keys.items() if key in keys}
        added = desired - current
        removed = current - desired
        changes.append({
            "profile": name,
            "created": created,
            "added": sorted(permission_keys[pk] for pk in added),
            "removed": sorted(permission_keys[pk] for pk in removed),
        })
        if not dry_run and (added or removed):
            if router.db_for_write(Group.permissions.through, instance=group) != using:
                raise ProfileConfigurationError(f"El router envía los permisos de {name} a otra base de datos.")
            group.permissions.set(permissions[pk] for pk in sorted(desired))
    return changes


def assign_default_profile(user):
    using = user._state.db
    membership = user.groups.through
    if (
        not router.allow_migrate_model(using, Group)
        or not router.allow_migrate_model(using, membership)
        or router.db_for_write(membership, instance=user) != using
    ):
        raise ProfileConfigurationError("El router envía la asignación del perfil a otra base de datos.")
    group, _ = Group.objects.using(using).get_or_create(name=DEFAULT_PROFILE)
    user.groups.add(group)
