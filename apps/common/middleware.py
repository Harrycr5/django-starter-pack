from contextvars import ContextVar

from rest_framework_simplejwt.authentication import JWTAuthentication

_actor = ContextVar("audit_actor", default=None)


def actor_id():
    user = _actor.get()
    return user.pk if user is not None and user.is_authenticated else None


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _actor.set(getattr(request, "user", None))
        try:
            return self.get_response(request)
        finally:
            _actor.reset(token)


class AuditedJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            _actor.set(result[0])
        return result
