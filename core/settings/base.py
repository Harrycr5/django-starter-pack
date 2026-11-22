from datetime import timedelta
from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

from apps.accounts.profiles import ADMIN_PROFILE, PROFILE_PERMISSIONS
from apps.common.utils import DATE_INPUT_FORMATS

BASE_DIR = Path(__file__).resolve().parents[2]
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-local-development-only")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes",
    "corsheaders", "rest_framework", "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular", "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
]
APPEND_SLASH = False
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "apps.common.exceptions.JsonErrorMiddleware",
    "apps.common.middleware.AuditMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF = "core.urls"
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"
DATABASES = {"default": env.db("DATABASE_URL")}
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("DATABASE_URL debe apuntar a PostgreSQL.")

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "APP_DIRS": True,
}]

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://starter")}
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"django.contrib.auth.password_validation.{validator}"}
    for validator in (
        "UserAttributeSimilarityValidator", "MinimumLengthValidator",
        "CommonPasswordValidator", "NumericPasswordValidator",
    )
]
LANGUAGE_CODE = "es"
TIME_ZONE = env("TIME_ZONE", default="UTC")
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="starter@example.com")

MINIMUM_AGE = env.int("MINIMUM_AGE", default=18)
PASSWORD_RESET_MINUTES = env.int("PASSWORD_RESET_MINUTES", default=10)
PASSWORD_RESET_MAX_ATTEMPTS = env.int("PASSWORD_RESET_MAX_ATTEMPTS", default=5)
REQUIRE_EMAIL_VERIFICATION = env.bool("REQUIRE_EMAIL_VERIFICATION", default=False)

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.common.middleware.AuditedJWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated", "apps.common.permissions.ModelPermissions",
    ],
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("LOGIN_RATE", default="10/min"),
        "forgot_password": env("FORGOT_PASSWORD_RATE", default="5/min"),
        "reset_password": env("RESET_PASSWORD_RATE", default="10/min"),
        "register": env("REGISTER_RATE", default="5/min"),
    },
    "DATE_INPUT_FORMATS": DATE_INPUT_FORMATS,
    "DEFAULT_SCHEMA_CLASS": "apps.common.schema.ApiSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
}
SIMPLE_JWT = {
    "SIGNING_KEY": env("JWT_SIGNING_KEY", default="local-development-key-do-not-use-in-production"),
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=5)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "CHECK_REVOKE_TOKEN": True,
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Django Starter API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {"deepLinking": True, "persistAuthorization": True},
}
