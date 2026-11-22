import re
from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from apps.accounts.models import PasswordResetCode

from conftest import PASSWORD, login, post

NEW_PASSWORD = "After!river653-cloud"

pytestmark = pytest.mark.django_db


def test_password_recovery(api, user, settings, mailoutbox, django_capture_on_commit_callbacks, monkeypatch):
    settings.PASSWORD_RESET_MAX_ATTEMPTS = 2
    sequence = iter([100001, 100002, 100003, 100004, 100005])
    monkeypatch.setattr("apps.accounts.services.secrets.randbelow", lambda _: next(sequence))
    session = login(api).data

    def issue_code():
        with django_capture_on_commit_callbacks(execute=True):
            response = post(api, "forgot-password", email=user.email)
        message = mailoutbox[-1]
        code = re.search(r"\b[0-9]{6}\b", message.body)[0]
        assert message.content_subtype == "plain"
        assert not message.alternatives
        saved = PasswordResetCode.objects.get(user=user)
        assert saved.code_hash != code and check_password(code, saved.code_hash)
        return response, code

    unknown = post(api, "forgot-password", email="missing@example.com")
    assert not mailoutbox
    response, expired = issue_code()
    assert unknown.data == response.data
    PasswordResetCode.objects.filter(user=user).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert post(api, "verify-code", email=user.email, code=expired).status_code == 400

    _, locked = issue_code()
    for _ in range(2):
        assert post(api, "verify-code", email=user.email, code="999999").status_code == 400
    assert PasswordResetCode.objects.get(user=user).failed_attempts == 2
    assert post(api, "reset-password", email=user.email, code=locked, password=NEW_PASSWORD).status_code == 400

    _, replaced = issue_code()
    _, current = issue_code()
    assert post(api, "verify-code", email=user.email, code=replaced).status_code == 400
    assert post(api, "verify-code", email=user.email, code=current).status_code == 204
    assert post(api, "reset-password", email=user.email, code=current, password=NEW_PASSWORD).status_code == 204
    assert post(api, "reset-password", email=user.email, code=current, password=PASSWORD).status_code == 400
    assert post(api, "refresh", refresh=session["refresh"]).status_code == 401
    assert login(api, password=NEW_PASSWORD).status_code == 200
