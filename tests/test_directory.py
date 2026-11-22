import pytest
from django.contrib.auth.models import Group, Permission
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User

from conftest import PASSWORD, login


@pytest.mark.django_db
def test_administrative_directory(api, user, system_profiles):
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
def test_administrator_cannot_assign_admin_or_modify_superuser(api, user, system_profiles):
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

    variant = Group.objects.create(name=" administrador ")
    assert api.patch(
        reverse("user-detail", args=[user.pk]), {"groups": [variant.pk]}, format="json",
    ).status_code == 400
    assert not user.groups.exists()

    api.force_authenticate(root)
    assert api.patch(
        reverse("user-detail", args=[user.pk]), {"groups": [admin_group.pk]}, format="json",
    ).status_code == 200


@pytest.mark.django_db
def test_reserved_profiles_cannot_be_created_renamed_or_deleted(api, user, system_profiles):
    user.is_superuser = True
    api.force_authenticate(user)
    custom = Group.objects.create(name="Soporte")
    custom_url = reverse("profile-detail", args=[custom.pk])

    for name in (" administrador ", "ADMINISTRADOR", "Ａdministrador", "usuario"):
        assert api.post(reverse("profile-list"), {"name": name}, format="json").status_code == 400
        assert api.patch(custom_url, {"name": name}, format="json").status_code == 400

    for name in ("Administrador", "Usuario", "uSuArIo"):
        group, _ = Group.objects.get_or_create(name=name)
        url = reverse("profile-detail", args=[group.pk])
        assert api.patch(url, {"name": "Otro"}, format="json").status_code == 400
        assert api.patch(url, {"permissions": []}, format="json").status_code == 400
        assert api.delete(url).status_code == 400

    custom.refresh_from_db()
    assert custom.name == "Soporte"


@pytest.mark.django_db
def test_django_admin_protects_reserved_groups(user, system_profiles):
    user.is_staff = user.is_superuser = True
    user.save(update_fields=["is_staff", "is_superuser"])
    client = Client()
    client.force_login(user)
    group = Group.objects.get(name="Administrador")
    custom = Group.objects.create(name="Soporte")

    assert client.post(reverse("admin:auth_group_change", args=[group.pk]), {"name": "Otro"}).status_code == 403
    assert client.post(reverse("admin:auth_group_delete", args=[group.pk]), {"post": "yes"}).status_code == 403
    assert client.post(reverse("admin:auth_group_add"), {"name": "ADMINISTRADOR"}).status_code == 200
    client.post(
        reverse("admin:auth_group_changelist"),
        {"action": "delete_selected", "_selected_action": [group.pk, custom.pk], "post": "yes"},
    )

    assert set(Group.objects.values_list("name", flat=True)) == {"Administrador", "Usuario", "Soporte"}
