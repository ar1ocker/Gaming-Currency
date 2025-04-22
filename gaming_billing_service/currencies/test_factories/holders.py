from currencies.models import Holder
from currencies.services import HoldersTypeService
from factory.declarations import LazyFunction, Sequence
from factory.django import DjangoModelFactory


class HoldersTestFactory(DjangoModelFactory):
    class Meta:
        model = Holder

    enabled = True
    holder_id = Sequence(lambda n: f"holder_id_{n}")
    holder_type = LazyFunction(HoldersTypeService.get_default)

    def __new__(cls, *args, **kwargs) -> Holder:
        return super().__new__(*args, **kwargs)
