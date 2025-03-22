from currencies.models import HolderType
from currencies.services import HoldersService, HoldersTypeService
from django.test import TestCase


class HolderServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder_type1 = HoldersTypeService.get_default()
        cls.holder_type2 = HolderType.objects.create(name="testholernameunique")

        return super().setUpTestData()

    def test_create_holder(self):
        holder = HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type1)
        self.assertEqual(holder.holder_id, "test")

    def test_double_create_holder(self):
        self.assertEqual(
            HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type1),
            HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type2),
        )
