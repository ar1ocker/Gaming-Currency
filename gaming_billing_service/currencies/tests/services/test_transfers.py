from datetime import timedelta
from decimal import Decimal

from currencies.models import (
    CheckingAccount,
    CurrencyService,
    CurrencyUnit,
    TransferRule,
)
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    HoldersService,
    HoldersTypeService,
    TransfersService,
)
from django.test import TestCase


class CurrencyTransferTransactionServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        holder_type = HoldersTypeService.get_default()

        cls.currency_unit = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")
        cls.service = CurrencyService.objects.create(name="servicename")
        cls.first_holder = HoldersService.get_or_create(holder_id="1", holder_type=holder_type)
        cls.second_holder = HoldersService.get_or_create(holder_id="2", holder_type=holder_type)

        cls.transfer_rule = TransferRule.objects.create(
            enabled=True,
            name="transferrule",
            unit=cls.currency_unit,
            fee_percent=Decimal(0),
            min_from_amount=Decimal(1),
        )

        return super().setUpTestData()

    def setUp(self):
        self.one_checking_account = AccountsService.get_or_create(
            holder=self.first_holder, currency_unit=self.currency_unit
        )
        self.two_checking_account = AccountsService.get_or_create(
            holder=self.second_holder, currency_unit=self.currency_unit
        )

    def add_amount(self, checking_account: CheckingAccount, amount: int):
        return AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
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
            transfer_rule=self.transfer_rule,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            from_amount=70,
            description="test",
        )

        self.assertEqual(transfer.from_checking_account, self.one_checking_account)
        self.assertEqual(transfer.to_checking_account, self.two_checking_account)

        self.assertEqual(transfer.from_amount, 70)
        self.assertEqual(transfer.description, "test")
        self.assertIsNone(transfer.closed_at)

    def test_takes_currency_from_source(self):
        self.add_amount(self.one_checking_account, 100)

        TransfersService.create(
            service=self.service,
            transfer_rule=self.transfer_rule,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            from_amount=70,
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
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=70,
                description="test",
            )

    def test_transfer_confirm(self):
        self.add_amount(self.one_checking_account, 100)

        transfer = TransfersService.confirm(
            transfer_transaction=TransfersService.create(
                service=self.service,
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=70,
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
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=70,
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
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=70,
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
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=70,
                description="test",
            ),
            status_description="teststatus",
        )

        with self.assertRaises(TransfersService.ValidationError):
            TransfersService.reject(transfer_transaction=rejected_transfer, status_description="")

    def test_transfer_with_different_currency_units(self):
        self.add_amount(self.one_checking_account, 100)

        currency_unit = CurrencyUnit.objects.create(symbol="sln", measurement="слоны")

        diff_currency_account = AccountsService.get_or_create(holder=self.second_holder, currency_unit=currency_unit)
        self.add_amount(diff_currency_account, 100)

        with self.assertRaisesRegex(TransfersService.ValidationError, "Transfer with unsuitable currency"):
            TransfersService.create(
                service=self.service,
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=diff_currency_account,
                from_amount=50,
                description="",
            )

        with self.assertRaisesRegex(TransfersService.ValidationError, "Transfer with unsuitable currency"):
            TransfersService.create(
                service=self.service,
                transfer_rule=self.transfer_rule,
                from_checking_account=diff_currency_account,
                to_checking_account=self.one_checking_account,
                from_amount=50,
                description="",
            )

    def test_transfer_to_same_account(self):
        self.add_amount(self.one_checking_account, 100)

        with self.assertRaisesRegex(TransfersService.ValidationError, ".*same account.*"):
            TransfersService.create(
                service=self.service,
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.one_checking_account,
                from_amount=50,
                description="",
            )

    def test_negative_amount_create(self):
        with self.assertRaisesRegex(AdjustmentsService.ValidationError, ".*from_amount < min_from_amount.*"):
            TransfersService.create(
                service=self.service,
                transfer_rule=self.transfer_rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=-50,
                description="",
            )

    def test_reject_outdated(self):
        self.add_amount(self.one_checking_account, 100)

        transaction1 = TransfersService.create(
            service=self.service,
            transfer_rule=self.transfer_rule,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            from_amount=10,
            description="test",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        transaction2 = TransfersService.create(
            service=self.service,
            transfer_rule=self.transfer_rule,
            from_checking_account=self.one_checking_account,
            to_checking_account=self.two_checking_account,
            from_amount=10,
            description="test",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        rejecteds = TransfersService.reject_all_outdated()
        self.assertEqual(len(rejecteds), 2)

        transaction1.refresh_from_db()
        transaction2.refresh_from_db()

        self.assertEqual(transaction1.status, "REJECTED")
        self.assertEqual(transaction2.status, "REJECTED")

    def test_transfer_rule_disabled(self):
        rule = TransferRule.objects.create(
            enabled=False, name="test", unit=self.currency_unit, fee_percent=Decimal(0), min_from_amount=Decimal(0)
        )

        with self.assertRaisesMessage(TransfersService.ValidationError, "Transfer is disabled"):
            TransfersService.create(
                service=self.service,
                transfer_rule=rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=10,
                description="test",
            )

    def test_transfer_rule_small_to_amount(self):
        rule = TransferRule.objects.create(
            enabled=True, name="test", unit=self.currency_unit, fee_percent=Decimal("110"), min_from_amount=Decimal(0)
        )

        with self.assertRaisesMessage(TransfersService.ValidationError, "from_amount is too small, to_amount <= 0"):
            TransfersService.create(
                service=self.service,
                transfer_rule=rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=10,
                description="test",
            )

    def test_transfer_rule_small_from_amount(self):
        rule = TransferRule.objects.create(
            enabled=True, name="test", unit=self.currency_unit, fee_percent=Decimal("0"), min_from_amount=Decimal(100)
        )

        with self.assertRaisesMessage(TransfersService.ValidationError, "from_amount < min_from_amount"):
            TransfersService.create(
                service=self.service,
                transfer_rule=rule,
                from_checking_account=self.one_checking_account,
                to_checking_account=self.two_checking_account,
                from_amount=10,
                description="test",
            )
