from importlib import import_module
from importlib.util import find_spec
from pkgutil import iter_modules

from django.core.exceptions import ImproperlyConfigured


def discover_api_patterns():
    package = import_module("apps")
    patterns = []
    for module in sorted(iter_modules(package.__path__), key=lambda module: module.name):
        if not module.ispkg:
            continue
        router_name = f"{package.__name__}.{module.name}.urls"
        if find_spec(router_name) is None:
            continue
        router = import_module(router_name)
        if not hasattr(router, "urlpatterns"):
            raise ImproperlyConfigured(f"{router_name} must define urlpatterns.")
        patterns.extend(router.urlpatterns)
    return patterns
