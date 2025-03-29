from currencies.models import CurrencyService
from django.conf import settings


class CurrencyServicesService:

    @classmethod
    def get_default(cls) -> CurrencyService:
        return CurrencyService.objects.get_or_create(name=settings.ADMIN_SITE_SERVICE_NAME)[0]
