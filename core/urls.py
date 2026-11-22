from django.apps import apps
from django.urls import include, path
from drf_spectacular.renderers import OpenApiJsonRenderer
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .routing import discover_api_patterns


class JsonSchemaRenderer(OpenApiJsonRenderer):
    media_type = "application/json"


schema_view = SpectacularAPIView.as_view(renderer_classes=[JsonSchemaRenderer])

urlpatterns = [
    path("api/schema/", schema_view, name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include(discover_api_patterns())),
]

if apps.is_installed("django.contrib.admin"):
    from apps.accounts.admin import admin_site

    urlpatterns.append(path("admin/", admin_site.urls))


handler400 = "apps.common.exceptions.bad_request"
handler403 = "apps.common.exceptions.forbidden"
handler404 = "apps.common.exceptions.not_found"
handler500 = "apps.common.exceptions.server_error"
