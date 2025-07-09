from datetime import datetime, timedelta
from decimal import Decimal
from itertools import chain
from typing import Literal

from currencies.models import (
    AdjustmentTransaction,
    CheckingAccount,
    CurrencyService,
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
    TransferRule,
    TransferTransaction,
)
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    ExchangesService,
    TransactionsService,
    TransfersService,
)
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from django.test import TestCase
from django.utils import timezone


class TransactionsTest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()
        cls.holder_1 = HoldersTestFactory()
        cls.holder_2 = HoldersTestFactory()

        cls.unit_1 = CurrencyUnitsTestFactory()
        cls.unit_2 = CurrencyUnitsTestFactory()

        cls.transfer_rule = TransferRule.objects.create(
            enabled=True,
            name="transferrulename",
            unit=cls.unit_1,
            fee_percent=Decimal("0"),
            min_from_amount=Decimal("1"),
        )

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
        )[0]
        self.checking_account_unit_2_user_1 = AccountsService.get_or_create(
            holder=self.holder_1, currency_unit=self.unit_2
        )[0]

        self.checking_account_unit_1_user_2 = AccountsService.get_or_create(
            holder=self.holder_2, currency_unit=self.unit_1
        )[0]
        self.checking_account_unit_2_user_2 = AccountsService.get_or_create(
            holder=self.holder_2, currency_unit=self.unit_2
        )[0]

    def create_adjustments(
        self,
        *,
        count: int,
        status: Literal["pending", "rejected", "confirmed"],
        checking_account: CheckingAccount,
        amount: Decimal | int,
        service: CurrencyService,
        created_at: datetime,
    ) -> list[AdjustmentTransaction]:

        ret_transactions = []

        for _ in range(count):
            transaction = AdjustmentsService.create(
                service=service, checking_account=checking_account, amount=amount, description=""
            )

            # Подделываем дату создания
            transaction.created_at = created_at
            transaction.save()

            match status:
                case "pending":
                    ret_transactions.append(transaction)
                case "confirmed":
                    ret_transactions.append(
                        AdjustmentsService.confirm(adjustment_transaction=transaction, status_description="")
                    )
                case "rejected":
                    ret_transactions.append(
                        AdjustmentsService.reject(adjustment_transaction=transaction, status_description="")
                    )
                case _:
                    self.fail("Error in calling the function")

        return ret_transactions

    def create_transfers(
        self,
        *,
        count: int,
        status: Literal["pending", "rejected", "confirmed"],
        from_account: CheckingAccount,
        to_account: CheckingAccount,
        amount: Decimal | int,
        service: CurrencyService,
        created_at: datetime,
    ) -> list[TransferTransaction]:
        ret_transactions = []

        for _ in range(count):
            transaction = TransfersService.create(
                service=service,
                transfer_rule=self.transfer_rule,
                from_checking_account=from_account,
                to_checking_account=to_account,
                from_amount=amount,
                description="",
            )

            # Подделываем дату создания
            transaction.created_at = created_at
            transaction.save()

            match status:
                case "pending":
                    ret_transactions.append(transaction)
                case "confirmed":
                    ret_transactions.append(
                        TransfersService.confirm(transfer_transaction=transaction, status_description="")
                    )
                case "rejected":
                    ret_transactions.append(
                        TransfersService.reject(transfer_transaction=transaction, status_description="")
                    )
                case _:
                    self.fail("Error in calling the function")

        return ret_transactions

    def create_exchanges(
        self,
        *,
        count: int,
        status: Literal["pending", "rejected", "confirmed"],
        holder: Holder,
        exchange_rule: ExchangeRule,
        from_unit: CurrencyUnit,
        to_unit: CurrencyUnit,
        from_amount: int,
        service: CurrencyService,
        created_at: datetime,
    ) -> list[ExchangeTransaction]:
        ret_transactions = []
        for _ in range(count):
            transaction = ExchangesService.create(
                service=service,
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

            match status:
                case "pending":
                    ret_transactions.append(transaction)
                case "confirmed":
                    ret_transactions.append(
                        ExchangesService.confirm(exchange_transaction=transaction, status_description="")
                    )
                case "rejected":
                    ret_transactions.append(
                        ExchangesService.reject(exchange_transaction=transaction, status_description="")
                    )
                case _:
                    self.fail("Error in calling the function")

        return ret_transactions

    def get_first_adjustment(self, checking_account: CheckingAccount):
        adjustment: AdjustmentTransaction = (
            AdjustmentTransaction.objects.filter(checking_account=checking_account).order_by("created_at").first()
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
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            service=self.service,
            created_at=self.old_datetime,
        )

        rejected_outdated_adjustments = self.create_adjustments(
            count=3,
            status="rejected",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            service=self.service,
            created_at=self.old_datetime,
        )

        not_outdated_adjustments = self.create_adjustments(
            count=3,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            service=self.service,
            created_at=self.now,
        )

        not_outdated_adjustments.extend(
            self.create_adjustments(
                count=3,
                status="rejected",
                checking_account=self.checking_account_unit_1_user_1,
                amount=100,
                service=self.service,
                created_at=self.now,
            )
        )

        pending_outdated_adjustments = self.create_adjustments(
            count=3,
            status="pending",
            checking_account=self.checking_account_unit_1_user_1,
            amount=10,
            service=self.service,
            created_at=self.old_datetime,
        )

        TransactionsService.collapse_old_transactions(
            old_than_timedelta=self.cutoff_timedelta, service_names=[self.service.name]
        )

        self.refresh_all_accounts()

        self.assertEqual(self.checking_account_unit_1_user_1.amount, 600, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_1_user_2.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_1.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_2.amount, 0, "Amount on other account has been changed")

        for adjustment in chain(confirmed_outdated_adjustments, rejected_outdated_adjustments):
            with self.assertRaises(AdjustmentTransaction.DoesNotExist):
                adjustment.refresh_from_db()

        try:
            for adjustment in chain(not_outdated_adjustments, pending_outdated_adjustments):
                adjustment.refresh_from_db()
        except AdjustmentTransaction.DoesNotExist:
            self.fail("Not outdated or pending adjustments has been deleted!")

        fake_transaction: AdjustmentTransaction = (
            AdjustmentTransaction.objects.filter(
                checking_account=self.checking_account_unit_1_user_1,
                status_description="Confirmed without real change amount in checking account",
            )
            .order_by("created_at")
            .first()  # type: ignore
        )

        self.assertEqual(fake_transaction.amount, 300)
        self.assertEqual(fake_transaction.status, "CONFIRMED")
        self.assertLess(fake_transaction.created_at, timezone.now() - self.cutoff_timedelta)
        self.assertIsNotNone(fake_transaction.closed_at)

    def test_remove_outdated_transfers(self):
        self.create_adjustments(
            count=1,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=2000,
            service=self.service,
            created_at=self.now,
        )
        self.create_adjustments(
            count=1,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_2,
            amount=2000,
            service=self.service,
            created_at=self.now,
        )

        outdated_transfers = self.create_transfers(
            count=3,
            status="confirmed",
            from_account=self.checking_account_unit_1_user_1,
            to_account=self.checking_account_unit_1_user_2,
            amount=300,
            service=self.service,
            created_at=self.old_datetime,
        )

        outdated_transfers.extend(
            self.create_transfers(
                count=3,
                status="rejected",
                from_account=self.checking_account_unit_1_user_1,
                to_account=self.checking_account_unit_1_user_2,
                amount=100,
                service=self.service,
                created_at=self.old_datetime,
            )
        )

        not_outdated_transfers = self.create_transfers(
            count=3,
            status="confirmed",
            from_account=self.checking_account_unit_1_user_1,
            to_account=self.checking_account_unit_1_user_2,
            amount=33,
            service=self.service,
            created_at=self.now,
        )

        not_outdated_transfers.extend(
            self.create_transfers(
                count=3,
                status="rejected",
                from_account=self.checking_account_unit_1_user_1,
                to_account=self.checking_account_unit_1_user_2,
                amount=100,
                service=self.service,
                created_at=self.now,
            )
        )

        pending_outdated_transfers = self.create_transfers(
            count=3,
            status="pending",
            from_account=self.checking_account_unit_1_user_1,
            to_account=self.checking_account_unit_1_user_2,
            amount=100,
            service=self.service,
            created_at=self.old_datetime,
        )

        TransactionsService.collapse_old_transactions(
            old_than_timedelta=self.cutoff_timedelta, service_names=[self.service.name]
        )

        self.refresh_all_accounts()

        self.assertEqual(self.checking_account_unit_1_user_1.amount, 701, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_1_user_2.amount, 2999, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_1.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_2.amount, 0, "Amount on other account has been changed")

        for transfer in outdated_transfers:
            with self.assertRaises(TransferTransaction.DoesNotExist):
                transfer.refresh_from_db()

        try:
            for transfer in chain(not_outdated_transfers, pending_outdated_transfers):
                transfer.refresh_from_db()
        except TransferTransaction.DoesNotExist:
            self.fail("Not outdated or pending transfer has been deleted!")

        fake_transaction_user_1 = self.get_first_adjustment(self.checking_account_unit_1_user_1)

        self.assertEqual(
            fake_transaction_user_1.status_description, "Confirmed without real change amount in checking account"
        )
        self.assertEqual(fake_transaction_user_1.amount, -900)
        self.assertEqual(fake_transaction_user_1.status, "CONFIRMED")
        self.assertLess(fake_transaction_user_1.created_at, timezone.now() - self.cutoff_timedelta)
        self.assertIsNotNone(fake_transaction_user_1.closed_at)

        fake_transaction_user_2 = self.get_first_adjustment(self.checking_account_unit_1_user_2)

        self.assertEqual(
            fake_transaction_user_2.status_description, "Confirmed without real change amount in checking account"
        )
        self.assertEqual(fake_transaction_user_2.amount, 900)
        self.assertEqual(fake_transaction_user_2.status, "CONFIRMED")
        self.assertLess(fake_transaction_user_2.created_at, timezone.now() - self.cutoff_timedelta)
        self.assertIsNotNone(fake_transaction_user_2.closed_at)

    def test_remove_outdated_exchanged(self):
        self.create_adjustments(
            count=1,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=10000,
            service=self.service,
            created_at=self.now,
        )
        self.create_adjustments(
            count=1,
            status="confirmed",
            checking_account=self.checking_account_unit_2_user_1,
            amount=10000,
            service=self.service,
            created_at=self.now,
        )

        outdated_exchanges = self.create_exchanges(
            count=3,
            status="confirmed",
            holder=self.holder_1,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit_1,
            to_unit=self.unit_2,
            from_amount=100,
            service=self.service,
            created_at=self.old_datetime,
        )  # для коллапсированной транзакции даст -300 для unit_1 и +3 у unit_2

        outdated_exchanges.extend(
            self.create_exchanges(
                count=3,
                status="rejected",
                holder=self.holder_1,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit_1,
                to_unit=self.unit_2,
                from_amount=100,
                service=self.service,
                created_at=self.old_datetime,
            )
        )  # для коллапсированной транзакции не должно дать ничего, ибо reject

        not_outdated_exchanges = self.create_exchanges(
            count=3,
            status="confirmed",
            holder=self.holder_1,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit_1,
            to_unit=self.unit_2,
            from_amount=200,
            service=self.service,
            created_at=self.now,
        )  # для коллапсированной транзакции не должно дать ничего, ибо дата новее чем cutoff_date

        not_outdated_exchanges.extend(
            self.create_exchanges(
                count=3,
                status="rejected",
                holder=self.holder_1,
                exchange_rule=self.exchange_rule,
                from_unit=self.unit_1,
                to_unit=self.unit_2,
                from_amount=200,
                service=self.service,
                created_at=self.now,
            )
        )  # для коллапсированной транзакции не должно дать ничего, ибо reject и дата новее чем cutoff_date

        pending_outdated_exchanges = self.create_exchanges(
            count=3,
            status="pending",
            holder=self.holder_1,
            exchange_rule=self.exchange_rule,
            from_unit=self.unit_1,
            to_unit=self.unit_2,
            from_amount=100,
            service=self.service,
            created_at=self.old_datetime,
        )  # для коллапсированной транзакции не должно дать ничего, хоть дата и старая, но транзакция pending

        TransactionsService.collapse_old_transactions(
            old_than_timedelta=self.cutoff_timedelta, service_names=[self.service.name]
        )

        self.refresh_all_accounts()

        # учитывается сумма и сколлапсированной транзакции и еще не сколлапсированной
        self.assertEqual(self.checking_account_unit_1_user_1.amount, 8800, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_1_user_2.amount, 0, "Amount on other account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_1.amount, 10009, "Amount on account has been changed")
        self.assertEqual(self.checking_account_unit_2_user_2.amount, 0, "Amount on other account has been changed")

        for exchange in outdated_exchanges:
            with self.assertRaises(ExchangeTransaction.DoesNotExist):
                exchange.refresh_from_db()

        try:
            for exchange in chain(not_outdated_exchanges, pending_outdated_exchanges):
                exchange.refresh_from_db()
        except ExchangeTransaction.DoesNotExist:
            self.fail("Not outdated or pending exchanges has been deleted!")

        fake_transaction_unit_1 = self.get_first_adjustment(self.checking_account_unit_1_user_1)

        self.assertEqual(
            fake_transaction_unit_1.status_description, "Confirmed without real change amount in checking account"
        )
        self.assertEqual(fake_transaction_unit_1.amount, -300)
        self.assertEqual(fake_transaction_unit_1.status, "CONFIRMED")
        self.assertLess(fake_transaction_unit_1.created_at, timezone.now() - self.cutoff_timedelta)
        self.assertIsNotNone(fake_transaction_unit_1.closed_at)

        fake_transaction_unit_2 = self.get_first_adjustment(self.checking_account_unit_2_user_1)

        self.assertEqual(
            fake_transaction_unit_2.status_description, "Confirmed without real change amount in checking account"
        )
        self.assertEqual(fake_transaction_unit_2.amount, 3)
        self.assertEqual(fake_transaction_unit_2.status, "CONFIRMED")
        self.assertLess(fake_transaction_unit_2.created_at, timezone.now() - self.cutoff_timedelta)
        self.assertIsNotNone(fake_transaction_unit_2.closed_at)

    def test_collapse_by_service(self):
        service_1 = CurrencyServicesTestFactory()
        service_2 = CurrencyServicesTestFactory()

        adjustments_service_1 = self.create_adjustments(
            count=3,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=100,
            service=service_1,
            created_at=self.old_datetime,
        )
        adjustments_service_2 = self.create_adjustments(
            count=3,
            status="confirmed",
            checking_account=self.checking_account_unit_1_user_1,
            amount=1000,
            service=service_2,
            created_at=self.old_datetime,
        )

        TransactionsService.collapse_old_transactions(
            old_than_timedelta=self.cutoff_timedelta, service_names=[service_1.name, service_2.name]
        )

        all_adjustments = AdjustmentsService.list()

        self.assertEqual(all_adjustments.count(), 2)

        self.assertEqual(all_adjustments.filter(service=service_1, amount=300).count(), 1)
        self.assertEqual(all_adjustments.filter(service=service_2, amount=3000).count(), 1)

        for adjustment in chain(adjustments_service_1, adjustments_service_2):
            with self.assertRaises(AdjustmentTransaction.DoesNotExist):
                adjustment.refresh_from_db()
