from functools import wraps

from currencies_api.models import CurrencyServiceAuth
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.validators import ValidationError

from .validators import BattlemetricsRequestHMACValidator, TimestampRequestHMACValidator


def hmac_service_auth(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        service_header = request.headers.get(settings.SERVICE_HEADER)

        if not service_header:
            raise AuthenticationFailed("Service header not found")

        try:
            service_auth = CurrencyServiceAuth.objects.select_related("service").get(service__name=service_header)
        except CurrencyServiceAuth.DoesNotExist:
            raise AuthenticationFailed("Service not found")

        if not service_auth.service.enabled:
            raise AuthenticationFailed("Service disabled")

        if settings.ENABLE_HMAC_VALIDATION:
            validator = None
            if service_auth.is_battlemetrics:
                validator = BattlemetricsRequestHMACValidator()
            else:
                validator = TimestampRequestHMACValidator()
            try:
                validator.validate_request(request=request, secret_key=service_auth.key)
            except ValidationError as e:
                raise AuthenticationFailed(e.detail)

        return func(self, request, service_auth, *args, **kwargs)

    return wrapper
