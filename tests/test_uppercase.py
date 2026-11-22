import pytest
from django.contrib.auth.models import Permission

from apps.accounts.models import User


@pytest.mark.django_db
def test_uppercase_leaves_django_permission_names_intact(user):
    user.last_name = "  pérez  "
    user.full_clean()
    assert user.last_name == "PÉREZ"
    user.last_name = " otro "
    user.save()
    assert User.objects.get(pk=user.pk).last_name == "OTRO"
    assert Permission.objects.get(
        content_type__app_label="accounts", codename="view_user",
    ).name == "Can view user"
