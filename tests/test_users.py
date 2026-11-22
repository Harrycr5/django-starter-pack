from datetime import date

import os
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import User

from conftest import PASSWORD, login, post

pytestmark = pytest.mark.django_db


def test_superuser_bypasses_group_assignment(api):
    admin = User.objects.create_superuser(
        "ADMIN@EXAMPLE.COM", PASSWORD, username="root", first_name="Root", last_name="User", birth_date=date(1980, 1, 1),
    )
    assert admin.is_superuser and admin.is_staff and not admin.groups.exists()
    tokens = login(api, admin.email).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api.get(reverse("accounts:me")).status_code == 200
    menu = api.get(reverse("accounts:menu")).data
    assert [node["path"] for node in menu] == ["/perfil", "/usuarios", "/perfiles", "/permisos"]


def test_inactive_user(api, user):
    user.is_active = False
    user.save(update_fields=["is_active"])
    assert login(api).status_code == 401


@pytest.mark.parametrize("birth_date", ["05/11/2004", "2004/11/05", "2004-11-05"])
def test_createsuperuser_accepts_birth_date_formats(api, birth_date):
    with patch.dict(os.environ, {"DJANGO_SUPERUSER_PASSWORD": PASSWORD}):
        call_command(
            "createsuperuser", interactive=False, email="root@example.com",
            username="Root", first_name="Nombre", last_name="Apellido",
            birth_date=birth_date, stdout=StringIO(),
        )
    account = User.objects.get(username="root")
    assert account.birth_date == date(2004, 11, 5)
    assert post(api, "login", username="ROOT", password=PASSWORD).status_code == 200
