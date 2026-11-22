import pytest
from django.contrib.auth.models import Group
from django.urls import reverse
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from conftest import PASSWORD, login, post

NEW_PASSWORD = "After!river653-cloud"

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("field", ["email", "username"])
def test_login_with_either_identifier(api, user, field):
    user.groups.add(Group.objects.get(name="Usuario"))
    identity = {field: getattr(user, field).upper()}
    assert post(api, "login", **identity, password="incorrecta").status_code == 401

    response = post(api, "login", **identity, password=PASSWORD)
    assert response.status_code == 200
    assert response.data["refresh"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    me = api.get(reverse("accounts:me"))
    assert me.status_code == 200
    assert me.json()["id"] == str(user.pk)


def test_optional_email_verification(api, settings, mailoutbox, django_capture_on_commit_callbacks):
    settings.REQUIRE_EMAIL_VERIFICATION = True
    with django_capture_on_commit_callbacks(execute=True):
        response = post(
            api, "register", email="new@example.com", username="nueva", first_name="Ana", last_name="Pérez",
            password=PASSWORD, password2=PASSWORD, birth_date="1990-01-01",
        )
    assert response.status_code == 201
    assert login(api, "new@example.com").status_code == 401
    token = mailoutbox[0].body.rsplit(" ", 1)[-1]
    assert post(api, "verify-email", token=token).status_code == 204
    assert post(api, "verify-email", token=token).status_code == 400
    assert login(api, "new@example.com").status_code == 200


def test_rotation_logout_and_password_change(api, user):
    original = login(api).data
    rotated = post(api, "refresh", refresh=original["refresh"])
    assert rotated.status_code == 200, rotated.data
    assert post(api, "refresh", refresh=original["refresh"]).status_code == 401
    assert post(api, "logout", refresh=rotated.data["refresh"]).status_code == 204
    assert post(api, "refresh", refresh=rotated.data["refresh"]).status_code == 401
    assert BlacklistedToken.objects.count() == 2

    session = login(api).data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {session['access']}")
    assert post(api, "change-password", current_password="incorrecta", password=NEW_PASSWORD).status_code == 400
    assert post(api, "change-password", current_password=PASSWORD, password=NEW_PASSWORD).status_code == 204
    assert api.get(reverse("accounts:me")).status_code == 401
    assert post(api, "refresh", refresh=session["refresh"]).status_code == 401
    assert login(api, password=NEW_PASSWORD).status_code == 200


def test_json_and_cors(api):
    assert api.get("/admin/").status_code == 404
    assert api.get("/admin/")["Content-Type"] == "application/json"
    assert api.get(reverse("accounts:login"), HTTP_ACCEPT="text/plain").status_code == 406
    docs = api.get("/api/docs/", HTTP_ACCEPT="text/html")
    assert docs.status_code == 200
    assert b"SwaggerUIBundle" in docs.content
    assert b'"persistAuthorization": true' in docs.content
    assert b"/api/schema/" in docs.content
    schema = api.get("/api/schema/", HTTP_ACCEPT="application/json")
    assert schema["Content-Type"] == "application/json"
    assert schema.json()["components"]["securitySchemes"]["jwtAuth"]["scheme"] == "bearer"
    for origin in ["http://localhost:5173", "http://localhost:3000"]:
        response = api.options(
            reverse("accounts:me"), HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type",
        )
        assert response["Access-Control-Allow-Origin"] == origin
        assert "authorization" in response["Access-Control-Allow-Headers"].lower()
