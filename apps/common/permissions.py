from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.permissions import DjangoModelPermissions


class ModelPermissions(DjangoModelPermissions):
    perms_map = {
        **DjangoModelPermissions.perms_map,
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
    }

    def has_permission(self, request, view):
        if request.method not in self.perms_map:
            return False
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            queryset = self._queryset(view)
        except AssertionError:
            return False
        method = "PATCH" if getattr(view, "action", None) == "restore" else request.method
        return request.user.has_perms(self.get_required_permissions(method, queryset.model))


def can_access_all_objects(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name=settings.ADMIN_PROFILE).exists())


class OwnObjectPermission(ModelPermissions):
    def has_object_permission(self, request, view, obj):
        if can_access_all_objects(request.user):
            return True
        owner_field = getattr(view, "owner_field", None)
        if owner_field is None:
            raise ImproperlyConfigured("Define owner_field para OwnObjectPermission.")
        return getattr(obj, owner_field) == request.user.pk
