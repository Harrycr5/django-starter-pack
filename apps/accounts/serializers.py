from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.common.serializers import UppercaseSerializerMixin

from . import services
from .models import User, normalize_email
from .profiles import ADMIN_PROFILE
from .signals import assign_default_profile


def validate_new_password(password, user):
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": exc.messages}) from exc


class RegisterSerializer(UppercaseSerializerMixin, serializers.ModelSerializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "birth_date", "email", "password", "password2")

    def validate_username(self, username):
        username = username.lower()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError("Este usuario ya existe.")
        return username

    def validate_email(self, email):
        email = normalize_email(email)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def validate(self, attrs):
        password = attrs["password"]
        if password != attrs.pop("password2"):
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        candidate = User(**{key: value for key, value in attrs.items() if key != "password"})
        validate_new_password(password, candidate)
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                pending = settings.REQUIRE_EMAIL_VERIFICATION
                user = User.objects.create_user(**validated_data, is_active=not pending, verification_pending=pending)
                assign_default_profile(user)
                if pending:
                    transaction.on_commit(lambda: services.send_verification(user))
                return user
        except (IntegrityError, DjangoValidationError) as exc:
            if User.objects.filter(email__iexact=validated_data["email"]).exists():
                raise serializers.ValidationError({"email": "Ya existe una cuenta con este correo."}) from exc
            if User.objects.filter(username__iexact=validated_data["username"]).exists():
                raise serializers.ValidationError({"username": "Este usuario ya existe."}) from exc
            raise


class AccountSerializer(UppercaseSerializerMixin, serializers.ModelSerializer):
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "birth_date", "groups", "permissions", "is_superuser")
        read_only_fields = ("username", "email", "is_superuser")

    def get_permissions(self, user) -> list[str]:
        return sorted(user.get_all_permissions())


class MenuSerializer(serializers.Serializer):
    label = serializers.CharField()
    path = serializers.CharField(allow_null=True)
    icon = serializers.CharField(allow_null=True)
    permission = serializers.CharField(allow_null=True)
    children = serializers.ListField(child=serializers.DictField())


class MessageSerializer(serializers.Serializer):
    detail = serializers.CharField()


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)


class CodeSerializer(EmailSerializer):
    code = serializers.RegexField(r"\A[0-9]{6}\Z")


class ResetPasswordSerializer(CodeSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=2048)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class LoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False
        self.fields["email"] = serializers.EmailField(max_length=254, required=False, write_only=True)
        self.fields["username"] = serializers.CharField(max_length=150, required=False, write_only=True)

    @transaction.atomic
    def validate(self, attrs):
        email = attrs.get("email")
        username = attrs.get("username")
        if bool(email) == bool(username):
            raise serializers.ValidationError("Envía el correo o el usuario.")
        users = User.objects.select_for_update().only("email")
        if username:
            user = users.filter(username=username.lower()).first()
            if user is None:
                # Run the normal authentication path with an identifier that cannot be an email.
                attrs["email"] = ""
            else:
                attrs["email"] = user.email
        else:
            attrs["email"] = normalize_email(email)
            users.filter(email=attrs["email"]).first()
        return super().validate(attrs)


class LockedRefreshSerializer(TokenRefreshSerializer):
    @transaction.atomic
    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        user = User.objects.select_for_update().filter(**{api_settings.USER_ID_FIELD: user_id}).first()
        if (
            user is None or not user.is_active
            or refresh.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password)
        ):
            raise InvalidToken("La sesión ya no es válida.")
        return super().validate(attrs)


class UserDirectorySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "is_active", "is_superuser", "groups")
        read_only_fields = ("username", "email", "first_name", "last_name", "is_active", "is_superuser")

    def validate_groups(self, groups):
        actor = self.context["request"].user
        if actor.is_superuser:
            return groups
        if any(group.name == ADMIN_PROFILE for group in groups):
            raise serializers.ValidationError("Solo un superusuario puede asignar el perfil Administrador.")
        granted = Permission.objects.filter(group__in=groups).values_list("content_type__app_label", "codename")
        if any(f"{app_label}.{codename}" not in actor.get_all_permissions() for app_label, codename in granted):
            raise serializers.ValidationError("Solo puedes asignar perfiles cuyos permisos tienes.")
        return groups


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ("id", "name", "permissions")

    def validate_name(self, name):
        if name in {ADMIN_PROFILE, *settings.PROFILE_PERMISSIONS}:
            raise serializers.ValidationError("Este nombre está reservado para un perfil del sistema.")
        return name

    def validate_permissions(self, permissions):
        user_permissions = self.context["request"].user.get_all_permissions()
        if any(f"{p.content_type.app_label}.{p.codename}" not in user_permissions for p in permissions):
            raise serializers.ValidationError("Solo puedes asignar permisos que tienes.")
        return permissions


class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label")
    model = serializers.CharField(source="content_type.model")
    key = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ("id", "name", "app_label", "model", "codename", "key")

    def get_key(self, permission) -> str:
        return f"{permission.content_type.app_label}.{permission.codename}"
