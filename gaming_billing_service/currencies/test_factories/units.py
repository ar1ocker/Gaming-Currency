from currencies.models import CurrencyUnit
from factory.declarations import Sequence
from factory.django import DjangoModelFactory


class CurrencyUnitsTestFactory(DjangoModelFactory):
    class Meta:
        model = CurrencyUnit

    symbol = Sequence(lambda n: f"cu_{n}")
    measurement = Sequence(lambda n: f"currency_measurement_{n}")
    precision = 4

    def __new__(cls, *args, **kwargs) -> CurrencyUnit:
        return super().__new__(*args, **kwargs)
