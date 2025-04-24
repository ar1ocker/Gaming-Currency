from currencies.models import CurrencyService
from django.conf import settings


def assemble_auth_headers(*, service: CurrencyService):
    return {settings.SERVICE_HEADER: service.name}
