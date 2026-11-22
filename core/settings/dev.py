from .base import *

DEBUG = env.bool("DEBUG", default=True)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173", "http://localhost:3000"])
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

if env.bool("ENABLE_DJANGO_ADMIN", default=True):
    INSTALLED_APPS = [
        *INSTALLED_APPS,
        "django.contrib.admin.apps.SimpleAdminConfig",
        "django.contrib.sessions",
        "django.contrib.messages",
        "django.contrib.staticfiles",
    ]
    MIDDLEWARE = [
        *MIDDLEWARE[:-2],
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        *MIDDLEWARE[-2:],
    ]
    TEMPLATES = [{**TEMPLATES[0], "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]}}]
    STATIC_URL = "/static/"
