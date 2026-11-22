from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.openapi import AutoSchema
from rest_framework.serializers import DateField

from .utils import DATE_INPUT_FORMATS


class ApiSchema(AutoSchema):
    def _map_serializer_field(self, field, direction, bypass_extensions=False):
        schema = super()._map_serializer_field(field, direction, bypass_extensions)
        if schema and isinstance(field, DateField):
            formats = getattr(field, "input_formats", DATE_INPUT_FORMATS)
            if tuple(formats) == DATE_INPUT_FORMATS:
                help_text = schema.get("description")
                accepted = "Acepta YYYY-MM-DD, DD/MM/YYYY y YYYY/MM/DD."
                schema["description"] = f"{help_text} {accepted}" if help_text else accepted
        return schema


class AuditedJWTScheme(SimpleJWTScheme):
    target_class = "apps.common.middleware.AuditedJWTAuthentication"
