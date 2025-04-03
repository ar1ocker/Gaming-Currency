from factory.django import DjangoModelFactory
from currencies_api.models import CurrencyServiceAuth


class CurrencyServiceAuthFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyServiceAuth

    key = "test_key"
    is_battlemetrics = False
