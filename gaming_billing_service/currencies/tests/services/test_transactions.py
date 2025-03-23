from datetime import timedelta

from currencies.models import CurrencyUnit, Service
from currencies.services import (
    AccountsService,
    HoldersService,
    HoldersTypeService,
    TransactionsService,
)
from django.test import TestCase


class CurrencyTransactionServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        holder_type = HoldersTypeService.get_default()

        cls.holder = HoldersService.get_or_create(holder_id="test", holder_type=holder_type)
        cls.service = Service.objects.create(name="servicename")
        cls.currency_unit = CurrencyUnit.objects.create(symbol="ppg", measurement="попугаи")

        return super().setUpTestData()

    def setUp(self):
        self.checking_account = AccountsService().get_or_create(holder=self.holder, currency_unit=self.currency_unit)

    def add_amount(self, amount):
        return TransactionsService().confirm(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=amount, description=""
            ),
            status_description="confirm",
        )

    def test_create(self):
        transaction = TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description="testdescr"
        )

        self.assertEqual(transaction.status, "PENDING")
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.description, "testdescr")
        self.assertEqual(transaction.status_description, "")
        self.assertIsNone(transaction.closed_at)

    def test_insufficient_amount_error(self):
        with self.assertRaises(TransactionsService.ValidationError):
            TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=-100, description=""
            )

    def test_positive_transaction_not_change_account_amount(self):
        TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description=""
        )

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_create_negative_transaction_substract_account_amount(self):
        self.add_amount(100)

        TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=-100, description=""
        )

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_confirm_positive_amount_adds_amount(self):
        transaction = TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description="testdescr"
        )

        transaction_confirmed = TransactionsService.confirm(currency_transaction=transaction, status_description="test")

        self.assertEqual(transaction_confirmed.status, "CONFIRMED")
        self.assertEqual(transaction_confirmed.status_description, "test")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 100)

    def test_confirm_negative_transaction_substract_amount(self):
        self.add_amount(100)

        negative_transaction = TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=-100, description=""
        )

        confirmed_negative_transaction = TransactionsService.confirm(
            currency_transaction=negative_transaction,
            status_description="negative",
        )

        self.assertEqual(confirmed_negative_transaction.status, "CONFIRMED")
        self.assertEqual(confirmed_negative_transaction.status_description, "negative")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_reject_positive_amount_not_change_amount(self):
        currency_transaction = TransactionsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description=""
        )

        transaction_rejected = TransactionsService.reject(
            currency_transaction=currency_transaction, status_description="reject"
        )

        self.assertEqual(transaction_rejected.status, "REJECTED")
        self.assertEqual(transaction_rejected.status_description, "reject")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_reject_negative_amount_return_amount_on_account(self):
        self.add_amount(100)

        transaction_rejected = TransactionsService.reject(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=-100, description=""
            ),
            status_description="reject",
        )

        self.assertEqual(transaction_rejected.status, "REJECTED")
        self.assertEqual(transaction_rejected.status_description, "reject")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 100)

    def test_confirm_rejected_transaction_raise_error(self):
        rejected_transaction = TransactionsService.reject(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(TransactionsService.ValidationError):
            TransactionsService.confirm(currency_transaction=rejected_transaction, status_description="")

    def test_confirm_confirmed_transaction_raise_error(self):
        confirmed_transaction = TransactionsService.confirm(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(TransactionsService.ValidationError):
            TransactionsService.confirm(currency_transaction=confirmed_transaction, status_description="")

    def test_reject_rejected_transaction_raise_error(self):
        rejected_transaction = TransactionsService.reject(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(TransactionsService.ValidationError):
            TransactionsService.reject(currency_transaction=rejected_transaction, status_description="")

    def test_reject_confirmed_transaction_raise_error(self):
        confirmed_transaction = TransactionsService.confirm(
            currency_transaction=TransactionsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(TransactionsService.ValidationError):
            TransactionsService.reject(currency_transaction=confirmed_transaction, status_description="")
            TransactionsService.reject(currency_transaction=confirmed_transaction, status_description="")
            TransactionsService.reject(currency_transaction=confirmed_transaction, status_description="")
            TransactionsService.reject(currency_transaction=confirmed_transaction, status_description="")

    def test_reject_outdated(self):
        transaction1 = TransactionsService.create(
            service=self.service,
            checking_account=self.checking_account,
            amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        transaction2 = TransactionsService.create(
            service=self.service,
            checking_account=self.checking_account,
            amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        rejecteds = TransactionsService.reject_all_outdated()
        self.assertEqual(len(rejecteds), 2)

        transaction1.refresh_from_db()
        transaction2.refresh_from_db()

        self.assertEqual(transaction1.status, "REJECTED")
        self.assertEqual(transaction2.status, "REJECTED")
