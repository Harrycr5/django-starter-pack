from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.common.pagination import StandardPagination
from apps.common.permissions import ModelPermissions, OwnObjectPermission, can_access_all_objects

from . import serializers, services
from .models import User
from .menu import ADMIN_MENU, MENU
from .throttles import LoginThrottle, RecoveryThrottle


class PublicEndpoint(generics.GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def parse(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]
    login_throttle_scope = "login"
    serializer_class = serializers.LoginSerializer


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
    serializer_class = serializers.LockedRefreshSerializer


class LogoutView(PublicEndpoint):
    serializer_class = serializers.LogoutSerializer

    @extend_schema(responses={204: None})
    @transaction.atomic
    def post(self, request):
        data = self.parse(request)
        try:
            token = RefreshToken(data["refresh"])
            user_id = token.get(api_settings.USER_ID_CLAIM)
            list(User.objects.select_for_update().filter(pk=user_id).values_list("pk", flat=True))
            token.check_blacklist()
            token.blacklist()
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(generics.CreateAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = serializers.RegisterSerializer
    throttle_scope = "register"


class VerifyEmailView(PublicEndpoint):
    serializer_class = serializers.EmailVerificationSerializer
    throttle_scope = "register"

    @extend_schema(responses={204: None})
    def post(self, request):
        if not services.verify_email(self.parse(request)["token"]):
            raise ValidationError({"token": "Token inválido o vencido."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.AccountSerializer
    permission_classes = [IsAuthenticated, OwnObjectPermission]
    http_method_names = ["get", "head", "patch", "options"]
    owner_field = "pk"

    def get_object(self):
        user = self.request.user
        self.check_object_permissions(self.request, user)
        return user


def filter_menu(nodes, permissions):
    return [
        {**node, "children": filter_menu(node.get("children", []), permissions)}
        for node in nodes
        if not node.get("permission") or node["permission"] in permissions
    ]


class MenuView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.MenuSerializer

    @extend_schema(responses=serializers.MenuSerializer(many=True))
    def get(self, request):
        menu = [*MENU, *ADMIN_MENU] if can_access_all_objects(request.user) else MENU
        return Response(filter_menu(menu, request.user.get_all_permissions()))


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.ChangePasswordSerializer

    @extend_schema(responses={204: None})
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            changed = services.change_password(
                request.user, serializer.validated_data["current_password"], serializer.validated_data["password"],
            )
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages}) from exc
        if not changed:
            raise ValidationError({"current_password": "La contraseña actual es incorrecta."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForgotPasswordView(PublicEndpoint):
    serializer_class = serializers.EmailSerializer
    throttle_classes = [RecoveryThrottle]
    recovery_throttle_scope = "forgot_password"

    @extend_schema(responses=serializers.MessageSerializer)
    def post(self, request):
        services.request_password_reset(self.parse(request)["email"])
        return Response({"detail": "Si la cuenta existe y está activa, recibirás un código."})


class VerifyCodeView(PublicEndpoint):
    serializer_class = serializers.CodeSerializer
    throttle_classes = [RecoveryThrottle]
    recovery_throttle_scope = "reset_password"

    @extend_schema(responses={204: None})
    def post(self, request):
        if not services.use_password_reset_code(**self.parse(request)):
            raise ValidationError({"code": "Código inválido o vencido."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class ResetPasswordView(PublicEndpoint):
    serializer_class = serializers.ResetPasswordSerializer
    throttle_classes = [RecoveryThrottle]
    recovery_throttle_scope = "reset_password"

    @extend_schema(responses={204: None})
    def post(self, request):
        data = self.parse(request)
        try:
            changed = services.use_password_reset_code(data["email"], data["code"], data["password"])
        except DjangoValidationError as exc:
            raise ValidationError({"password": exc.messages}) from exc
        if not changed:
            raise ValidationError({"code": "Código inválido o vencido."})
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdministrativeModelPermission(ModelPermissions):
    def has_permission(self, request, view):
        return can_access_all_objects(request.user) and super().has_permission(request, view)


class UserDirectoryViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.prefetch_related("groups").order_by("email")
    serializer_class = serializers.UserDirectorySerializer
    permission_classes = [AdministrativeModelPermission]
    pagination_class = StandardPagination
    http_method_names = ["get", "head", "options", "patch"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "partial_update":
            queryset = queryset.select_for_update()
            if not self.request.user.is_superuser:
                queryset = queryset.filter(is_superuser=False).exclude(groups__name=settings.ADMIN_PROFILE)
        return queryset

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.prefetch_related("permissions").order_by("name")
    serializer_class = serializers.ProfileSerializer
    permission_classes = [AdministrativeModelPermission]
    pagination_class = StandardPagination

    def require_editable(self, group):
        if group.name in {settings.ADMIN_PROFILE, *settings.PROFILE_PERMISSIONS}:
            raise ValidationError({"name": "Este perfil se administra en la configuración."})

    def perform_update(self, serializer):
        self.require_editable(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.require_editable(instance)
        instance.delete()


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.select_related("content_type").order_by("content_type__app_label", "codename")
    serializer_class = serializers.PermissionSerializer
    permission_classes = [AdministrativeModelPermission]
    pagination_class = StandardPagination
