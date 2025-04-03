from django.core.exceptions import ValidationError as DjangoValidationError, PermissionDenied
from rest_framework import exceptions
from rest_framework.serializers import as_serializer_error
from rest_framework.views import exception_handler


def django_validation_error_exception_handler(exc, ctx):
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(as_serializer_error(exc))

    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied(str(exc))

    response = exception_handler(exc, ctx)

    if response is None:
        return None

    detail = None
    if isinstance(exc.detail, (list, dict)):
        detail = response.data
    else:
        detail = response.data["detail"]  # type: ignore

    data = {}

    if isinstance(exc, exceptions.ValidationError):
        data["message"] = "Validation error"
        data["extra"] = {"fields": detail}
    else:
        data["message"] = detail
        data["extra"] = {}

    response.data = data

    return response
