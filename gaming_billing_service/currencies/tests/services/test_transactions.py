from datetime import datetime, timedelta
from itertools import chain
from typing import Literal

from currencies.models import (
    AdjustmentTransaction,
    CheckingAccount,
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
    HolderType,
    Service,
    TransferTransaction,
)
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    ExchangesService,
    HoldersService,
    TransactionsService,
    TransfersService,
)
from django.test import TestCase
from django.utils import timezone


class TransactionsTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = Service.objects.create(name="test")
        cls.holder_type = HolderType.get_default()
        cls.holder_1 = HoldersService.get_or_create(holder_id="test", holder_type=cls.holder_type)
        cls.holder_2 = HoldersService.get_or_create(holder_id="test2", holder_type=cls.holder_type)

        cls.unit_1 = CurrencyUnit.objects.create(symbol="unit_1", measurement="unit_1_measurement")
        cls.unit_2 = CurrencyUnit.objects.create(symbol="unit_2", measurement="unit_2_measurement")

        cls.exchange_rule = ExchangeRule.objects.create(
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=cls.unit_1,
            second_unit=cls.unit_2,
            forward_rate=100,
            reverse_rate=80,
            min_first_amount=1,
            min_second_amount=1,
        )

        cls.now = timezone.now()
        cls.cutoff_timedelta = timedelta(days=1)
        cls.old_datetime = cls.now - timedelta(days=2)

    def setUp(self) -> None:
        self.checking_account_unit_1_user_1 = AccountsService.get_or_create(
            holder=self.holder_1, currency_unit=self.unit_1
        )
        self.checking_account_unit_2_user_1 = AccountsService.get_or_create(
            holder=self.holder_1, currency_unit=self.unit_2
        )

        self.checking_account_unit_1_user_2 = AccountsService.get_or_create(
            holder=self.holder_2, currency_unit=self.unit_1
        )
        self.checking_account_unit_2_user_2 = AccountsService.get_or_create(
            holder=self.holder_2, currency_unit=self.unit_2
        )

    def create_adjustments(
        self,
        *,
        count: int,
        status: Literal["r", "c"],
        checking_account: CheckingAccount,
        amount: int,
        created_at: datetime
    ) -> list[AdjustmentTransaction]:

        ret_transactions = []

        for _ in range(count):
            transaction = AdjustmentsService.create(
                service=self.service, checking_account=checking_account, amount=amount, description=""
            )

            # Подделываем дату создания
            transaction.created_at = created_at
            transaction.save()

            if status == "r":
                ret_transactions.append(
                    AdjustmentsService.reject(adjustment_transaction=transaction, status_description="")
                )
            else:
                ret_transactions.append(
                    AdjustmentsService.confirm(adjustment_transaction=transaction, status_description="")
                )

        return ret_transactions

    def create_transfers(
        self,
        count: int,
        status: Literal["r", "c"],
        from_account: CheckingAccount,
        to_account: CheckingAccount,
        amount: int,
        created_at: datetime,
    ) -> list[TransferTransaction]:
        ret_transactions = []

        for _ in range(count):
            transaction = TransfersService.create(
                service=self.service,
                from_checking_account=from_account,
                to_checking_account=to_account,
                amount=amount,
                description="",
            )

            # Подделываем дату создания
            transaction.created_at = created_at
            transaction.save()

            if status == "r":
                ret_transactions.append(
                    TransfersService.reject(transfer_transaction=transaction, status_description="")
                )
            else:
                ret_transactions.append(
                    TransfersService.confirm(transfer_transaction=transaction, status_description="")
                )

        return ret_transactions

    def create_exchanges(
        self,
        *,
        count: int,
        status: Literal["r", "c"],
        holder: Holder,
        exchange_rule: ExchangeRule,
        from_unit: CurrencyUnit,
        to_unit: CurrencyUnit,
        from_amount: int,
        created_at: datetime
    ) -> list[ExchangeTransaction]:
        ret_transactions = []
        for _ in range(count):
            transaction = ExchangesService.create(
                service=self.service,
                holder=holder,
                exchange_rule=exchange_rule,
                from_unit=from_unit,
                to_unit=to_unit,
                from_amount=from_amount,
                description="",
            )

            # Подделываем дату создания
            transaction.created_at = created_at
            transaction.save()

            if status == "r":
                ret_transactions.append(
                    ExchangesService.reject(exchange_transaction=transaction, status_description="")
                )
            else:
                ret_transactions.append(
                    ExchangesService.confirm(exchange_transaction=transaction, status_description="")
                )

        return ret_transactions

    def get_first_adjustment(self, checking_account: CheckingAccount):
        adjustment: AdjustmentTransaction = (
            AdjustmentTransaction.objects.filter(checking_account=checking_account).order_by("-created_at").first()
        )  # type: ignore

        return adjustment

    def refresh_all_accounts(self):
        self.checking_account_unit_1_user_1.refresh_from_db()
        self.checking_account_unit_1_user_2.refresh_from_db()
        self.checking_account_unit_2_user_1.refresh_from_db()
        self.checking_account_unit_2_user_2.refresh_from_db()

    def test_remove_outdated_adjustments(self):

        confirmed_outdated_adjustments = self.create_adjustments(
            count=3,
            status="c",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            created_at=self.old_datetime,
        )

        rejected_outdated_adjustments = self.create_adjustments(
            count=3,
            status="r",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            created_at=self.old_datetime,
        )

        not_outdated_adjustments = self.create_adjustments(
            count=3, status="c", checking_account=self.checking_account_unit_1_user_1, amount=100, created_at=self.now
        )

        not_outdated_adjustments.extend(
            self.create_adjustments(
                count=3,
                status="r",
                checking_account=self.checking_account_unit_1_user_1,
                amount=100,
                created_at=self.now,
            )
        )

        TransactionsService.collapse_old_transactions(old_than_timedelta=self.cutoff_timedelta)

        self.refresh_all_accounts()

        self.assertEqual(self.checking_account_unit_1_user_1.amount, 600, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_1_user_2.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_1.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_2.amount, 0, "Amount on other account has been changed")

        for adjustment in chain(confirmed_outdated_adjustments, rejected_outdated_adjustments):
            with self.assertRaises(AdjustmentTransaction.DoesNotExist):
                adjustment.refresh_from_db()

        try:
            for adjustment in not_outdated_adjustments:
                adjustment.refresh_from_db()
        except AdjustmentTransaction.DoesNotExist:
            self.fail("Not outdated adjustments has been deleted!")

        fake_transaction = self.get_first_adjustment(self.checking_account_unit_1_user_1)

        self.assertEqual(fake_transaction.amount, 300)
        self.assertEqual(fake_transaction.status, "CONFIRMED")
        self.assertIsNotNone(fake_transaction.closed_at)
        self.assertIsNotNone(fake_transaction.status_description)

    def test_remove_outdated_transfers(self):
        self.create_adjustments(
            count=1, status="c", checking_account=self.checking_account_unit_1_user_1, amount=2000, created_at=self.now
        )
        self.create_adjustments(
            count=1, status="c", checking_account=self.checking_account_unit_1_user_2, amount=2000, created_at=self.now
        )

        outdated_transfers = self.create_transfers(
            count=3,
            status="c",
            from_account=self.checking_account_unit_1_user_1,
            to_account=self.checking_account_unit_1_user_2,
            amount=300,
            created_at=self.old_datetime,
        )

        outdated_transfers.extend(
            self.create_transfers(
                count=3,
                status="r",
                from_account=self.checking_account_unit_1_user_1,
                to_account=self.checking_account_unit_1_user_2,
                amount=100,
                created_at=self.old_datetime,
            )
        )

        not_outdated_transfers = self.create_transfers(
            count=3,
            status="c",
            from_account=self.checking_account_unit_1_user_1,
            to_account=self.checking_account_unit_1_user_2,
            amount=33,
            created_at=self.now,
        )

        not_outdated_transfers.extend(
            self.create_transfers(
                count=3,
                status="r",
                from_account=self.checking_account_unit_1_user_1,
                to_account=self.checking_account_unit_1_user_2,
                amount=100,
                created_at=self.now,
            )
        )

        TransactionsService.collapse_old_transactions(old_than_timedelta=self.cutoff_timedelta)

        self.refresh_all_accounts()

        self.assertEqual(self.checking_account_unit_1_user_1.amount, 1001, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_1_user_2.amount, 2999, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_1.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_2.amount, 0, "Amount on other account has been changed")

        for transfer in outdated_transfers:
            with self.assertRaises(TransferTransaction.DoesNotExist):
                transfer.refresh_from_db()

        try:
            for transfer in not_outdated_transfers:
                transfer.refresh_from_db()
        except TransferTransaction.DoesNotExist:
            self.fail("Not outdated transfer has been deleted!")
