import pytest
from django.contrib.auth.models import Group, Permission
from django.urls import reverse

from apps.accounts.models import User

from conftest import PASSWORD, login


@pytest.mark.django_db
def test_administrative_directory(api, user):
    admin = User.objects.create_superuser(
        "root@example.com", PASSWORD, username="root",
        first_name=user.first_name, last_name=user.last_name, birth_date=user.birth_date,
    )
    user.groups.add(Group.objects.get(name="Usuario"))
    for name in ("user-list", "profile-list", "permission-list"):
        assert api.get(reverse(name)).status_code == 401

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login(api).data['access']}")
    for name in ("user-list", "profile-list", "permission-list"):
        assert api.get(reverse(name)).status_code == 403

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login(api, admin.email).data['access']}")
    assert api.get(reverse("user-list")).json()["count"] == 2
    user_url = reverse("user-detail", args=[user.pk])
    assert api.get(user_url).json()["id"] == str(user.pk)
    permission = Permission.objects.get(content_type__app_label="accounts", codename="view_user")
    assert api.get(reverse("permission-detail", args=[permission.pk])).json()["key"] == "accounts.view_user"
    assert api.get(reverse("permission-list")).json()["count"] > 0
    assert api.get(reverse("profile-list")).json()["count"] == 2
    created = api.post(reverse("profile-list"), {"name": "Soporte", "permissions": [permission.pk]}, format="json")
    assert created.status_code == 201, created.data
    profile_id = created.data["id"]
    profile_url = reverse("profile-detail", args=[profile_id])
    assert api.patch(profile_url, {"name": "Soporte técnico"}, format="json").status_code == 200
    assert api.patch(user_url, {"groups": [profile_id]}, format="json").json()["groups"] == [profile_id]
    reserved_url = reverse("profile-detail", args=[Group.objects.get(name="Usuario").pk])
    assert api.delete(reserved_url).status_code == 400
    assert api.delete(profile_url).status_code == 204


@pytest.mark.django_db
def test_administrator_cannot_assign_admin_or_modify_superuser(api, user):
    root = User.objects.create_superuser(
        "root@example.com", PASSWORD, username="root",
        first_name=user.first_name, last_name=user.last_name, birth_date=user.birth_date,
    )
    delegate = User.objects.create_user(
        "delegate@example.com", PASSWORD, username="delegate",
        first_name=user.first_name, last_name=user.last_name, birth_date=user.birth_date,
    )
    admin_group = Group.objects.get(name="Administrador")
    delegate.groups.add(admin_group)
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {login(api, delegate.email).data['access']}")
    assert api.get(reverse("permission-list")).status_code == 200
    assert api.patch(reverse("user-detail", args=[root.pk]), {"groups": []}, format="json").status_code == 404
    assert api.patch(
        reverse("user-detail", args=[user.pk]), {"groups": [admin_group.pk]}, format="json",
    ).status_code == 400
