from django import forms
from django.contrib.admin import AdminSite
from django.contrib.admin.forms import AdminAuthenticationForm
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError

from .forms import AccountChangeForm, AccountCreationForm
from .models import User
from .profiles import is_reserved_profile


class AccountAdmin(UserAdmin):
    form = AccountChangeForm
    add_form = AccountCreationForm
    list_display = ("username", "email", "first_name", "last_name", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("created_at", "created_by", "updated_at", "updated_by")
    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        ("Perfil", {"fields": ("first_name", "last_name", "birth_date")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Auditoría", {"fields": ("last_login", "date_joined", *readonly_fields)}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": (*AccountCreationForm.Meta.fields, "password1", "password2")}),
    )


class DevelopmentAdminLoginForm(AdminAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_superuser:
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login", params={
                "username": self.username_field.verbose_name,
            })


class DevelopmentAdminSite(AdminSite):
    login_form = DevelopmentAdminLoginForm

    def has_permission(self, request):
        return super().has_permission(request) and request.user.is_superuser


class ProfileAdminForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "permissions")

    def clean_name(self):
        name = self.cleaned_data["name"]
        if is_reserved_profile(name):
            raise forms.ValidationError("Este nombre está reservado para un perfil del sistema.")
        return name


class ProfileAdmin(GroupAdmin):
    form = ProfileAdminForm

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or not is_reserved_profile(obj.name))

    def has_delete_permission(self, request, obj=None):
        return super().has_delete_permission(request, obj) and (obj is None or not is_reserved_profile(obj.name))

    def get_deleted_objects(self, objs, request):
        deleted, counts, permissions, protected = super().get_deleted_objects(objs, request)
        protected.extend(str(group) for group in objs if is_reserved_profile(group.name))
        return deleted, counts, permissions, protected


admin_site = DevelopmentAdminSite()
admin_site.register(User, AccountAdmin)
admin_site.register(Group, ProfileAdmin)
