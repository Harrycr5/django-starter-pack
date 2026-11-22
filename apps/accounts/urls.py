from django.urls import include, path
from rest_framework.routers import SimpleRouter

from . import views


auth_patterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("verify-code/", views.VerifyCodeView.as_view(), name="verify-code"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="reset-password"),
    path("me/", views.MeView.as_view(), name="me"),
    path("me/menu/", views.MenuView.as_view(), name="menu"),
]

router = SimpleRouter()
router.register("users", views.UserDirectoryViewSet, basename="user")
router.register("profiles", views.ProfileViewSet, basename="profile")
router.register("permissions", views.PermissionViewSet, basename="permission")

urlpatterns = [path("auth/", include((auth_patterns, "accounts"))), *router.urls]
