from currencies.models import CurrencyService
from factory.declarations import Sequence
from factory.django import DjangoModelFactory


class CurrencyServicesTestFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyService

    name = Sequence(lambda n: f"service_{n}")
    enabled = True
    permissions = {"root": True}
