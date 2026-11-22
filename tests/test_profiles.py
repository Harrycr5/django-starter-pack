from uuid import UUID

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User

from conftest import PASSWORD, login, post

pytestmark = pytest.mark.django_db


def test_registration_login_permissions_and_menu(api):
    assert Group.objects.filter(name="Usuario").exists()
    assert Group.objects.get(name="Administrador").permissions.count() == Permission.objects.count()
    call_command("setup_profiles")
    permission = Permission.objects.get(content_type__app_label="accounts", codename="view_user")
    assert permission.name == "Can view user"
    invalid = post(
        api, "register", email="new@example.com", username="nueva", first_name="Ana", last_name="Pérez",
        password=PASSWORD, password2=PASSWORD, birth_date=str(timezone.localdate()),
    )
    assert invalid.status_code == 400

    response = post(
        api, "register", email="New@EXAMPLE.COM", username="Nueva", first_name=" ana ", last_name=" pérez ",
        password=PASSWORD, password2=PASSWORD, birth_date="01/01/1990",
    )
    assert response.status_code == 201, response.data
    assert response.data["last_name"] == "PÉREZ"
    tokens = login(api, "NEW@example.com").data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    me = api.get(reverse("accounts:me")).json()
    assert UUID(me["id"]).version == 4
    assert me["username"] == "nueva"
    assert me["birth_date"] == "1990-01-01"
    assert me["email"] == "new@example.com"
    assert me["groups"] == ["Usuario"]
    assert me["permissions"] == ["accounts.change_user", "accounts.view_user"]
    assert me["is_superuser"] is False
    assert [node["label"] for node in api.get(reverse("accounts:menu")).data] == ["Mi perfil"]
    result = api.patch(reverse("accounts:me"), {"first_name": " eva ", "birth_date": "1991/01/02", "is_superuser": True}, format="json")
    assert result.data["first_name"] == "EVA"
    assert result.data["birth_date"] == "1991-01-02"
    user = User.objects.get(pk=me["id"])
    assert user.updated_by_id == user.pk and not user.is_superuser
