from django.apps import apps as installed_apps
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.db import router, transaction

from .profiles import ADMIN_PROFILE, DEFAULT_PROFILE


def setup_profiles(using="default"):
    with transaction.atomic(using=using):
        _sync_profile_permissions(using)


def _sync_profile_permissions(using):
    permissions = Permission.objects.using(using).select_related("content_type")
    by_key = {f"{p.content_type.app_label}.{p.codename}": p for p in permissions}
    groups = Group.objects.using(using)
    admin, _ = groups.get_or_create(name=ADMIN_PROFILE)
    admin.permissions.set(by_key.values())
    for name, keys in settings.PROFILE_PERMISSIONS.items():
        if name == ADMIN_PROFILE:
            continue
        group, _ = groups.get_or_create(name=name)
        group.permissions.set(by_key[key] for key in keys)


def sync_profiles(sender, using, apps=installed_apps, **kwargs):
    migrated = [config.label for config in installed_apps.get_app_configs() if config.models_module]
    if not migrated or sender.label != migrated[-1] or not router.allow_migrate_model(using, Group):
        return
    try:
        apps.get_model("accounts", "User")
    except LookupError:
        return
    setup_profiles(using)


def assign_default_profile(user):
    group, _ = Group.objects.using(user._state.db).get_or_create(name=DEFAULT_PROFILE)
    user.groups.add(group)
