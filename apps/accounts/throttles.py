from rest_framework.throttling import ScopedRateThrottle


class LoginThrottle(ScopedRateThrottle):
    scope_attr = "login_throttle_scope"


class RecoveryThrottle(ScopedRateThrottle):
    scope_attr = "recovery_throttle_scope"
