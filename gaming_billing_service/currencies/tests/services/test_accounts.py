from currencies.models import CurrencyUnit, HolderType
from currencies.services import AccountsService, HoldersService
from django.test import TestCase


class CheckingAccountServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder_type = HolderType.get_default()
        return super().setUpTestData()

    def setUp(self):
        self.holder = HoldersService.get_or_create(holder_id="test", holder_type=self.holder_type)
        self.currency_unit = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")

    def test_create_checking_account(self):
        checking_account = AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit)
        self.assertEqual(checking_account.amount, 0)

    def test_double_create_checking_account(self):
        self.assertEqual(
            AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit),
            AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit),
        )
