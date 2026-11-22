from unicodedata import normalize

from django.conf import settings


ADMIN_PROFILE = "Administrador"
DEFAULT_PROFILE = "Usuario"

PROFILE_PERMISSIONS = {
    DEFAULT_PROFILE: ("accounts.view_user", "accounts.change_user"),
}


def normalize_profile_name(name):
    return normalize("NFKC", name).strip().casefold()


def is_reserved_profile(name):
    reserved = {ADMIN_PROFILE, DEFAULT_PROFILE, *settings.PROFILE_PERMISSIONS}
    return normalize_profile_name(name) in {normalize_profile_name(value) for value in reserved}
