from datetime import timedelta
from decimal import Decimal

from currencies.models import CurrencyService, CurrencyUnit, Holder
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
)
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from django.test import TestCase


class AdjustmentTransactionServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holder = HoldersTestFactory()
        cls.service = CurrencyServicesService.get_default()
        cls.currency_unit = CurrencyUnitsTestFactory()

        return super().setUpTestData()

    def setUp(self):
        self.checking_account = AccountsService().get_or_create(holder=self.holder, currency_unit=self.currency_unit)[0]

    def add_amount(self, amount):
        return AdjustmentsService().confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=amount, description=""
            ),
            status_description="confirm",
        )

    def test_create(self):
        transaction = AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description="testdescr"
        )

        self.assertEqual(transaction.status, "PENDING")
        self.assertEqual(transaction.amount, 100)
        self.assertEqual(transaction.description, "testdescr")
        self.assertEqual(transaction.status_description, "")
        self.assertIsNone(transaction.closed_at)

    def test_insufficient_amount_error(self):
        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=-100, description=""
            )

    def test_zero_amount_error(self):
        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=0, description=""
            )

    def test_positive_transaction_not_change_account_amount(self):
        AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description=""
        )

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_create_negative_transaction_substract_account_amount(self):
        self.add_amount(100)

        AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=-100, description=""
        )

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_confirm_positive_amount_adds_amount(self):
        transaction = AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description="testdescr"
        )

        transaction_confirmed = AdjustmentsService.confirm(
            adjustment_transaction=transaction, status_description="test"
        )

        self.assertEqual(transaction_confirmed.status, "CONFIRMED")
        self.assertEqual(transaction_confirmed.status_description, "test")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 100)

    def test_confirm_negative_transaction_substract_amount(self):
        self.add_amount(100)

        negative_transaction = AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=-100, description=""
        )

        confirmed_negative_transaction = AdjustmentsService.confirm(
            adjustment_transaction=negative_transaction,
            status_description="negative",
        )

        self.assertEqual(confirmed_negative_transaction.status, "CONFIRMED")
        self.assertEqual(confirmed_negative_transaction.status_description, "negative")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_reject_positive_amount_not_change_amount(self):
        adjustment_transaction = AdjustmentsService.create(
            service=self.service, checking_account=self.checking_account, amount=100, description=""
        )

        transaction_rejected = AdjustmentsService.reject(
            adjustment_transaction=adjustment_transaction, status_description="reject"
        )

        self.assertEqual(transaction_rejected.status, "REJECTED")
        self.assertEqual(transaction_rejected.status_description, "reject")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 0)

    def test_reject_negative_amount_return_amount_on_account(self):
        self.add_amount(100)

        transaction_rejected = AdjustmentsService.reject(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=-100, description=""
            ),
            status_description="reject",
        )

        self.assertEqual(transaction_rejected.status, "REJECTED")
        self.assertEqual(transaction_rejected.status_description, "reject")

        self.checking_account.refresh_from_db()
        self.assertEqual(self.checking_account.amount, 100)

    def test_confirm_rejected_transaction_raise_error(self):
        rejected_transaction = AdjustmentsService.reject(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.confirm(adjustment_transaction=rejected_transaction, status_description="")

    def test_confirm_confirmed_transaction_raise_error(self):
        confirmed_transaction = AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.confirm(adjustment_transaction=confirmed_transaction, status_description="")

    def test_reject_rejected_transaction_raise_error(self):
        rejected_transaction = AdjustmentsService.reject(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.reject(adjustment_transaction=rejected_transaction, status_description="")

    def test_reject_confirmed_transaction_raise_error(self):
        confirmed_transaction = AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=self.service, checking_account=self.checking_account, amount=100, description=""
            ),
            status_description="reject",
        )

        with self.assertRaises(AdjustmentsService.ValidationError):
            AdjustmentsService.reject(adjustment_transaction=confirmed_transaction, status_description="")

    def test_reject_outdated(self):
        transaction1 = AdjustmentsService.create(
            service=self.service,
            checking_account=self.checking_account,
            amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        transaction2 = AdjustmentsService.create(
            service=self.service,
            checking_account=self.checking_account,
            amount=100,
            description="",
            auto_reject_timedelta=timedelta(seconds=-1),
        )

        rejecteds = AdjustmentsService.reject_all_outdated()
        self.assertEqual(len(rejecteds), 2)

        transaction1.refresh_from_db()
        transaction2.refresh_from_db()

        self.assertEqual(transaction1.status, "REJECTED")
        self.assertEqual(transaction2.status, "REJECTED")

    def test_amount_precision_raise_error(self):
        with self.assertRaisesRegex(
            AdjustmentsService.ValidationError, "Число знаков после запятой у валюты больше чем возможно.*"
        ):
            AdjustmentsService.create(
                service=self.service,
                checking_account=self.checking_account,
                amount=Decimal("100.00001"),
                description="",
            )


class AdjustmentListServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service_1: CurrencyService = CurrencyServicesTestFactory()
        cls.service_2: CurrencyService = CurrencyServicesTestFactory()

        cls.holder_1: Holder = HoldersTestFactory()
        cls.holder_2: Holder = HoldersTestFactory()

        cls.unit_1: CurrencyUnit = CurrencyUnitsTestFactory()
        cls.unit_2: CurrencyUnit = CurrencyUnitsTestFactory()

        cls.account_1_unit_1 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_1)[0]
        cls.account_1_unit_2 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_2)[0]

        cls.account_2_unit_1 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_1)[0]
        cls.account_2_unit_2 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_2)[0]

        cls.pending_adjustments = [
            AdjustmentsService.create(
                service=cls.service_1, checking_account=cls.account_1_unit_1, amount=100, description=""
            )
            for _ in range(3)
        ]

        cls.rejected_adjustments = [
            AdjustmentsService.reject(
                adjustment_transaction=AdjustmentsService.create(
                    service=cls.service_2, checking_account=cls.account_2_unit_1, amount=1000, description=""
                ),
                status_description="",
            )
            for _ in range(3)
        ]

        cls.confirmed_adjustments = [
            AdjustmentsService.confirm(
                adjustment_transaction=AdjustmentsService.create(
                    service=cls.service_1, checking_account=cls.account_2_unit_2, amount=10, description=""
                ),
                status_description="",
            )
            for _ in range(3)
        ]

    def test_list_service(self):
        service_1_adjustments = AdjustmentsService.list(filters=dict(service=self.service_1.name))

        self.assertEqual(service_1_adjustments.count(), 6)

        for adjustment in service_1_adjustments:
            self.assertEqual(adjustment.service.name, self.service_1.name)

    def test_list_status(self):
        confirmed = AdjustmentsService.list(filters=dict(status="confirmed"))

        self.assertEqual(confirmed.count(), 3)

        for adjustment in confirmed:
            self.assertEqual(adjustment.status, "CONFIRMED")

    def test_list_holder(self):
        adjustments_with_holders_1 = AdjustmentsService.list(filters=dict(holder=self.holder_1.holder_id))

        self.assertEqual(adjustments_with_holders_1.count(), 3)

        for adjustment in adjustments_with_holders_1:
            self.assertEqual(adjustment.checking_account.holder.holder_id, self.holder_1.holder_id)

    def test_list_unit(self):
        adjustments_with_unit_1 = AdjustmentsService.list(filters=dict(currency_unit=self.unit_1.symbol))

        self.assertEqual(adjustments_with_unit_1.count(), 6)

        for adjustment in adjustments_with_unit_1:
            self.assertEqual(adjustment.checking_account.currency_unit.symbol, self.unit_1.symbol)

    def test_list_amount(self):
        adjustments_with_amount_100 = AdjustmentsService.list(
            filters=dict(amount_min=Decimal("99"), amount_max=Decimal("101"))
        )

        self.assertEqual(adjustments_with_amount_100.count(), 3)

        for adjustment in adjustments_with_amount_100:
            self.assertEqual(adjustment.amount, 100)

    def test_list_ordering(self):
        ordering_adjustments = AdjustmentsService.list(filters=dict(ordering="-amount"))

        self.assertEqual(ordering_adjustments.first().amount, 1000)  # type: ignore
        self.assertEqual(ordering_adjustments.last().amount, 10)  # type: ignore
