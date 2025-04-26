from currencies.models import HolderType
from currencies.services import AccountsService
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from django.test import TestCase


class CheckingAccountServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder_type = HolderType.get_default()
        return super().setUpTestData()

    def setUp(self):
        self.holder = HoldersTestFactory()
        self.currency_unit = CurrencyUnitsTestFactory()

    def test_create_checking_account(self):
        checking_account = AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit)[0]
        self.assertEqual(checking_account.amount, 0)

    def test_double_create_checking_account(self):
        self.assertEqual(
            AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit)[0],
            AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit)[0],
        )

    def test_get(self):
        AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit)[0]

        self.assertIsNotNone(AccountsService.get(holder=self.holder, currency_unit=self.currency_unit))

    def test_get_does_not_exists(self):
        self.assertIsNone(AccountsService.get(holder=self.holder, currency_unit=self.currency_unit))
