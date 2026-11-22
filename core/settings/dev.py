from .base import *

DEBUG = env.bool("DEBUG", default=True)
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:5173", "http://localhost:3000"])
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
