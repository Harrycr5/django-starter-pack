from uuid import uuid4

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.contrib.auth.validators import ASCIIUsernameValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from apps.common.mixins import UppercaseFieldsMixin
from apps.common.models import AuditModel

from .fields import BirthDateField
from .validators import validate_birth_date


def normalize_email(email):
    return email.strip().lower()


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, username):
        return super().get_by_natural_key(normalize_email(username))

    async def aget_by_natural_key(self, username):
        return await super().aget_by_natural_key(normalize_email(username))

    def create_user(self, email, password=None, **fields):
        if not email or not email.strip():
            raise ValueError("El correo electrónico es obligatorio.")
        if "username" in fields:
            fields["username"] = fields["username"].strip().lower()
        user = self.model(email=normalize_email(email), **fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **fields):
        fields.setdefault("is_staff", True)
        fields.setdefault("is_superuser", True)
        fields.setdefault("is_active", True)
        if not all(fields[key] is True for key in ("is_staff", "is_superuser", "is_active")):
            raise ValueError("El superusuario debe estar activo y tener acceso administrativo.")
        return self.create_user(email, password, **fields)


class User(UppercaseFieldsMixin, AuditModel, AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    username = models.CharField("usuario", max_length=150, unique=True, validators=[ASCIIUsernameValidator()])
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    birth_date = BirthDateField(validators=[validate_birth_date])
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    verification_pending = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True, editable=False)

    uppercase_fields = ("first_name", "last_name")
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name", "birth_date"]
    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
            models.UniqueConstraint(Lower("username"), name="accounts_user_username_ci_unique"),
        ]

    def clean(self):
        self.email = normalize_email(self.email)
        self.username = self.username.strip().lower()
        super().clean()

    def save(self, *args, **kwargs):
        self.email = normalize_email(self.email)
        self.username = self.username.strip().lower()
        return super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


class PasswordResetCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="password_reset_code")
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    failed_attempts = models.PositiveIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
