from currencies.models import HolderType
from factory.declarations import Sequence
from factory.django import DjangoModelFactory


class HoldersTypeTestFactory(DjangoModelFactory):
    class Meta:
        model = HolderType

    name = Sequence(lambda n: f"holder_type_{n}")

    def __new__(cls, *args, **kwargs) -> HolderType:
        return super().__new__(*args, **kwargs)
