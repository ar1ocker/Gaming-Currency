from currencies.models import CurrencyUnit
from currencies.services import AccountsService, PlayersService
from django.test import TestCase


class CheckingAccountServicesTests(TestCase):
    def setUp(self):
        self.player = PlayersService.get_or_create(player_id="test")
        self.currency_unit = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")

    def test_create_checking_account(self):
        checking_account = AccountsService.get_or_create(player=self.player, currency_unit=self.currency_unit)
        self.assertEqual(checking_account.amount, 0)

    def test_double_create_checking_account(self):
        self.assertEqual(
            AccountsService.get_or_create(player=self.player, currency_unit=self.currency_unit),
            AccountsService.get_or_create(player=self.player, currency_unit=self.currency_unit),
        )
