from django.http import JsonResponse
from rest_framework.views import exception_handler


def error_payload(status, details):
    return {"error": {"status": status, "details": details}}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data = error_payload(response.status_code, response.data)
    return response


def bad_request(request, exception):
    return JsonResponse(error_payload(400, {"detail": "Solicitud inválida."}), status=400)


def forbidden(request, exception):
    return JsonResponse(error_payload(403, {"detail": "Acceso denegado."}), status=403)


def not_found(request, exception):
    return JsonResponse(error_payload(404, {"detail": "Recurso no encontrado."}), status=404)


def server_error(request):
    return JsonResponse(error_payload(500, {"detail": "Error interno."}), status=500)


class JsonErrorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "").partition(";")[0]
        if response.status_code >= 400 and content_type != "application/json" and not content_type.endswith("+json"):
            response.content = JsonResponse(
                error_payload(response.status_code, {"detail": response.reason_phrase}),
            ).content
            response["Content-Type"] = "application/json"
        return response
