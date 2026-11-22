from datetime import date

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User

PASSWORD = "Start!winter419-sky"


@pytest.fixture(autouse=True)
def test_auth_settings(settings):
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        "  USER@example.com ", PASSWORD, username="ana", first_name=" ana ",
        last_name=" pérez ", birth_date=date(1990, 1, 1),
    )


def post(api, endpoint, **data):
    return api.post(reverse(f"accounts:{endpoint}"), data, format="json")


def login(api, email="USER@EXAMPLE.COM", password=PASSWORD):
    return post(api, "login", email=email, password=password)
