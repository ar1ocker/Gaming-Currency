from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain

from currencies.models import (
    AdjustmentTransaction,
    ExchangeTransaction,
    TransferTransaction,
)
from currencies.utils import retry_on_serialization_error
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone


class TransactionsService:

    @classmethod
    def collapse_old_transactions(cls, *, old_than_timedelta: timedelta):
        now = timezone.now()
        cutoff_date = now - old_than_timedelta

        # Cуммы для AdjustmentTransaction
        adjustment_sums = (
            AdjustmentTransaction.objects.filter(created_at__lt=cutoff_date, status="CONFIRMED")
            .values("checking_account")
            .annotate(total_amount=Sum("amount"))
        )

        # Cуммы для TransferTransaction (входящие и исходящие)
        transfer_sums_in = (
            TransferTransaction.objects.filter(created_at__lt=cutoff_date, status="CONFIRMED")
            .values(checking_account=F("to_checking_account"))
            .annotate(total_amount=Sum("to_amount"))
        )

        transfer_sums_out = (
            TransferTransaction.objects.filter(created_at__lt=cutoff_date, status="CONFIRMED")
            .values(checking_account=F("from_checking_account"))
            .annotate(total_amount=Sum("from_amount") * -1)  # Учитываем исходящие транзакции как отрицательные
        )

        # Cуммы для ExchangeTransaction (входящие и исходящие)
        exchange_sums_in = (
            ExchangeTransaction.objects.filter(created_at__lt=cutoff_date, status="CONFIRMED")
            .values(checking_account=F("to_checking_account"))
            .annotate(total_amount=Sum("to_amount"))
        )

        exchange_sums_out = (
            ExchangeTransaction.objects.filter(created_at__lt=cutoff_date, status="CONFIRMED")
            .values(checking_account=F("from_checking_account"))
            .annotate(total_amount=Sum("from_amount") * -1)  # Учитываем исходящие транзакции как отрицательные
        )

        # для хранения итоговых сумм по каждому аккаунту
        total_amounts = defaultdict(int)

        for item in chain(adjustment_sums, transfer_sums_in, transfer_sums_out, exchange_sums_in, exchange_sums_out):
            total_amounts[item["checking_account"]] += item["total_amount"]

        cls._create_fake_transaction_and_remove_old(
            total_amounts=total_amounts, cutoff_date=cutoff_date, closed_date=now
        )

    @classmethod
    @retry_on_serialization_error()
    def _create_fake_transaction_and_remove_old(cls, *, total_amounts, cutoff_date: datetime, closed_date: datetime):
        with transaction.atomic():
            # Создаем AdjustmentTransaction для каждого аккаунта
            # Удаляем старые транзакции
            AdjustmentTransaction.objects.filter(created_at__lt=cutoff_date).delete()
            TransferTransaction.objects.filter(created_at__lt=cutoff_date).delete()
            ExchangeTransaction.objects.filter(created_at__lt=cutoff_date).delete()

            for account_id, total_amount in total_amounts.items():
                AdjustmentTransaction.objects.create(
                    description="The amount of old collapsed transactions",
                    status="CONFIRMED",
                    status_description="Confirmed without real change amount in checking account",
                    auto_reject_after=closed_date,
                    created_at=cutoff_date,
                    closed_at=closed_date,
                    checking_account_id=account_id,
                    amount=total_amount,
                )
