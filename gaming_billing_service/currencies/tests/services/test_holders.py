from currencies.services import HoldersService, HoldersTypeService
from currencies.test_factories import HoldersTestFactory, HoldersTypeTestFactory
from django.test import TestCase


class HoldersServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder_type1 = HoldersTypeTestFactory()
        cls.holder_type2 = HoldersTypeTestFactory()

        return super().setUpTestData()

    def test_create_holder(self):
        holder = HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type1)
        self.assertEqual(holder.holder_id, "test")

    def test_double_create_holder(self):
        self.assertEqual(
            HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type1),
            HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type2),
        )

    def test_holder_does_not_exists(self):
        self.assertIsNone(HoldersService.get(holder_id="notfound"))


class HoldersServiceListTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder_type_1 = HoldersTypeTestFactory()
        cls.holder_type_2 = HoldersTypeTestFactory()

        cls.type_1_holders = [HoldersTestFactory(holder_type=cls.holder_type_1) for _ in range(3)]
        cls.type_2_holders = [HoldersTestFactory(holder_type=cls.holder_type_2) for _ in range(3)]

    def test_list_all(self):
        self.assertEqual(HoldersService.list().count(), 6)

    def test_list_holder_type_2(self):
        holder_type_2_holders = HoldersService.list(filters=dict(holder_type=self.holder_type_2.name))

        self.assertEqual(holder_type_2_holders.count(), 3)

        for holder in holder_type_2_holders:
            self.assertEqual(holder.holder_type, self.holder_type_2)


class HoldersTypeServiceTests(TestCase):
    def test_get_exists(self):
        holder_type = HoldersTypeTestFactory()

        self.assertEqual(HoldersTypeService.get(name=holder_type.name), holder_type)  # type: ignore

    def test_get_does_not_exists(self):
        self.assertIsNone(HoldersTypeService.get(name="not_exists"))
