import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.core.signing import BadSignature, TimestampSigner
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from .models import PasswordResetCode, User, normalize_email

logger = logging.getLogger(__name__)


def send_reset_code(recipient, code, minutes):
    subject = "Código de recuperación"
    expiry = f"Caduca en {minutes} minutos. Si no solicitaste este código, ignora el correo."
    try:
        send_mail(subject, f"{subject}: {code}\n{expiry}", None, [recipient])
    except (OSError, ValueError):
        logger.exception("No se pudo enviar el correo de recuperación.")


def send_verification(user):
    token = TimestampSigner(salt="accounts.verify-email").sign_object([str(user.pk), user.email])
    try:
        send_mail("Verifica tu correo", f"Token de verificación (24 horas): {token}", None, [user.email])
    except (OSError, ValueError):
        logger.exception("No se pudo enviar el correo de verificación.")


@transaction.atomic
def verify_email(token):
    try:
        pk, email = TimestampSigner(salt="accounts.verify-email").unsign_object(token, max_age=86400)
    except BadSignature:
        return False
    user = User.objects.select_for_update().filter(pk=pk, email=email, verification_pending=True).first()
    if user is None:
        return False
    user.email_verified_at = timezone.now()
    user.is_active = True
    user.verification_pending = False
    user.save(update_fields=["email_verified_at", "is_active", "verification_pending"])
    return True


def blacklist_refresh_tokens(user):
    tokens = OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now())
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token_id=pk) for pk in tokens.values_list("pk", flat=True)],
        ignore_conflicts=True,
    )


def request_password_reset(email):
    code = f"{secrets.randbelow(1_000_000):06d}"
    code_hash = make_password(code)
    with transaction.atomic():
        user = User.objects.select_for_update().filter(email=normalize_email(email), is_active=True).first()
        if user is None:
            return
        PasswordResetCode.objects.update_or_create(user=user, defaults={
            "code_hash": code_hash,
            "expires_at": timezone.now() + timedelta(minutes=settings.PASSWORD_RESET_MINUTES),
            "failed_attempts": 0,
            "used_at": None,
        })
        minutes = settings.PASSWORD_RESET_MINUTES
        transaction.on_commit(lambda: send_reset_code(user.email, code, minutes))


@transaction.atomic
def use_password_reset_code(email, code, new_password=None):
    user = User.objects.select_for_update().filter(email=normalize_email(email), is_active=True).first()
    reset = PasswordResetCode.objects.filter(user=user).first() if user else None
    now = timezone.now()
    if (
        reset is None or reset.used_at is not None or reset.expires_at <= now
        or reset.failed_attempts >= settings.PASSWORD_RESET_MAX_ATTEMPTS
    ):
        make_password(code)
        return False
    if not check_password(code, reset.code_hash):
        reset.failed_attempts += 1
        reset.save(update_fields=["failed_attempts"])
        return False
    if new_password is not None:
        validate_password(new_password, user)
        user.set_password(new_password)
        user.save(update_fields=["password"])
        blacklist_refresh_tokens(user)
        reset.used_at = now
        reset.save(update_fields=["used_at"])
    return True


@transaction.atomic
def change_password(user, current_password, new_password):
    user = User.objects.select_for_update().get(pk=user.pk)
    if not user.is_active or not user.check_password(current_password):
        return False
    validate_password(new_password, user)
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_refresh_tokens(user)
    PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
    return True
