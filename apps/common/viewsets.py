from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.response import Response


@extend_schema_view(list=extend_schema(parameters=[
    OpenApiParameter("active", str, enum=["true", "false", "all"]),
]))
class BaseViewSet(viewsets.ModelViewSet):
    allow_restore = False

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "restore":
            return queryset.filter(is_active=False)
        active = self.request.query_params.get("active", "true")
        if active == "true":
            return queryset.filter(is_active=True)
        if active not in {"false", "all"}:
            raise ValidationError({"active": "Usa true, false o all."})
        if not self.allow_restore:
            raise ValidationError({"active": "El acceso a registros inactivos está deshabilitado."})
        return queryset if active == "all" else queryset.filter(is_active=False)

    def perform_destroy(self, instance):
        instance.delete()

    @extend_schema(request=None, responses={204: None})
    @action(detail=True, methods=["post"])
    def restore(self, request, *args, **kwargs):
        if not self.allow_restore:
            raise MethodNotAllowed(request.method)
        self.get_object().restore()
        return Response(status=status.HTTP_204_NO_CONTENT)
