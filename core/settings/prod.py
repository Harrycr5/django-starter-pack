from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False
SECRET_KEY = env("SECRET_KEY")
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": env("JWT_SIGNING_KEY")}
if SECRET_KEY.startswith("django-insecure-") or min(len(SECRET_KEY), len(SIMPLE_JWT["SIGNING_KEY"])) < 32:
    raise ImproperlyConfigured("Configura claves de producción de al menos 32 caracteres.")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if env.bool("TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
