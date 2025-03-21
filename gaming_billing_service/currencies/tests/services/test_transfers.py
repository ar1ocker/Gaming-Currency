from currencies.models import CheckingAccount, CurrencyUnit, Service
from currencies.services import (
    AccountsService,
    PlayersService,
    TransactionsService,
    TransfersService,
)
from django.test import TestCase


class CurrencyTransferTransactionServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.currency_unit = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")
        cls.service = Service.objects.create(name="servicename")
        cls.first_player = PlayersService.get_or_create(player_id="1")
        cls.second_player = PlayersService.get_or_create(player_id="2")

        return super().setUpTestData()

    def setUp(self):
        self.one_checking_account = AccountsService.get_or_create(
            player=self.first_player, currency_unit=self.currency_unit
        )
        self.two_checking_account = AccountsService.get_or_create(
            player=self.second_player, currency_unit=self.currency_unit
        )

    def add_amount(self, checking_account: CheckingAccount, amount: int):
        return TransactionsService.confirm(
            currency_transaction=TransactionsService.create(
                service=self.service,
                checking_account=checking_account,
                amount=amount,
                description="",
            ),
            status_description="confirm",
        )

    def test_transfer_create(self):
        self.add_amount(self.one_checking_account, 100)

        transfer = TransfersService.create(
            service=self.service,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            amount=70,
            description="test",
        )

        self.assertEqual(transfer.from_checking_account, self.one_checking_account)
        self.assertEqual(transfer.to_checking_account, self.two_checking_account)

        self.assertEqual(transfer.amount, 70)
        self.assertEqual(transfer.description, "test")
        self.assertIsNone(transfer.closed_at)

    def test_takes_currency_from_source(self):
        self.add_amount(self.one_checking_account, 100)

        TransfersService.create(
            service=self.service,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            amount=70,
            description="test",
        )

        self.one_checking_account.refresh_from_db()
        self.two_checking_account.refresh_from_db()
        self.assertEqual(self.one_checking_account.amount, 30)
        self.assertEqual(self.two_checking_account.amount, 0)

    def test_insufficient_amount(self):
        with self.assertRaises(TransfersService.ValidationError):
            TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=70,
                description="test",
            )

    def test_transfer_confirm(self):
        self.add_amount(self.one_checking_account, 100)

        transfer = TransfersService.confirm(
            transfer_transaction=TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=70,
                description="test",
            ),
            status_description="teststatus",
        )

        self.assertEqual(transfer.status, "CONFIRMED")
        self.assertEqual(transfer.status_description, "teststatus")
        self.assertIsNotNone(transfer.closed_at)

        self.one_checking_account.refresh_from_db()
        self.two_checking_account.refresh_from_db()
        self.assertEqual(self.one_checking_account.amount, 30)
        self.assertEqual(self.two_checking_account.amount, 70)

    def test_transfer_reject(self):
        self.add_amount(self.one_checking_account, 100)

        transfer = TransfersService.reject(
            transfer_transaction=TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=70,
                description="test",
            ),
            status_description="teststatus",
        )

        self.assertEqual(transfer.status, "REJECTED")
        self.assertEqual(transfer.status_description, "teststatus")
        self.assertIsNotNone(transfer.closed_at)

        self.one_checking_account.refresh_from_db()
        self.two_checking_account.refresh_from_db()
        self.assertEqual(self.one_checking_account.amount, 100)
        self.assertEqual(self.two_checking_account.amount, 0)

    def test_transfer_confirm_rejected_error(self):
        self.add_amount(self.one_checking_account, 100)

        rejected_transfer = TransfersService.reject(
            transfer_transaction=TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=70,
                description="test",
            ),
            status_description="teststatus",
        )

        with self.assertRaises(TransfersService.ValidationError):
            TransfersService.confirm(transfer_transaction=rejected_transfer, status_description="")

    def test_error_transfer_confirm_rejected_error(self):
        self.add_amount(self.one_checking_account, 100)

        rejected_transfer = TransfersService.confirm(
            transfer_transaction=TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=70,
                description="test",
            ),
            status_description="teststatus",
        )

        with self.assertRaises(TransfersService.ValidationError):
            TransfersService.reject(transfer_transaction=rejected_transfer, status_description="")

    def test_transfer_with_different_currency_units(self):
        self.add_amount(self.one_checking_account, 100)

        currency_unit = CurrencyUnit.objects.create(symbol="sln", measurement="слоны")

        diff_currency_account = AccountsService.get_or_create(player=self.second_player, currency_unit=currency_unit)
        self.add_amount(diff_currency_account, 100)

        with self.assertRaisesRegex(TransfersService.ValidationError, ".*different currency units.*"):
            TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=diff_currency_account,
                amount=50,
                description="",
            )

        with self.assertRaisesRegex(TransfersService.ValidationError, ".*different currency units.*"):
            TransfersService.create(
                service=self.service,
                from_checking_account=diff_currency_account,
                to_checking_account=self.one_checking_account,
                amount=50,
                description="",
            )

    def test_transfer_to_same_account(self):
        self.add_amount(self.one_checking_account, 100)

        with self.assertRaisesRegex(TransfersService.ValidationError, ".*same account.*"):
            TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.one_checking_account,
                amount=50,
                description="",
            )

    def test_negative_amount_create(self):
        with self.assertRaisesRegex(
            TransactionsService.ValidationError, ".*Ensure this value is greater than or equal to 0.*"
        ):
            TransfersService.create(
                service=self.service,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                amount=-50,
                description="",
            )
