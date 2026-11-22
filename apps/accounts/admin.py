from django.contrib.admin import ModelAdmin

from .forms import AccountChangeForm, AccountCreationForm
from .models import User


class AccountAdmin(ModelAdmin):
    form = AccountChangeForm
    list_display = ("username", "email", "first_name", "last_name", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = AccountCreationForm
        return super().get_form(request, obj, **kwargs)


def register(site):
    site.register(User, AccountAdmin)
