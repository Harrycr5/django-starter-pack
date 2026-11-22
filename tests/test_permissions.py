import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from conftest import login


@pytest.mark.django_db
def test_view_permission_is_required_for_get(api, user):
    user.user_permissions.add(Permission.objects.get(
        content_type__app_label="accounts", codename="change_user",
    ))
    tokens = login(api).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    url = reverse("accounts:me")
    assert api.get(url).status_code == 403
    assert api.head(url).status_code == 403
    assert api.patch(url, {"first_name": " Ana "}, format="json").status_code == 200

    user.user_permissions.add(Permission.objects.get(
        content_type__app_label="accounts", codename="view_user",
    ))
    assert api.get(url).json()["id"] == str(user.pk)
