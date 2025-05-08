from currencies_api.models import CurrencyServiceAuth
from factory.django import DjangoModelFactory


class CurrencyServiceAuthTestFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyServiceAuth

    key = "test_key"
    is_battlemetrics = False

    def __new__(cls, *args, **kwargs) -> CurrencyServiceAuth:
        return super().__new__(*args, **kwargs)
