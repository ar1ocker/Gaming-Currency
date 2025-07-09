from collections import defaultdict
from datetime import datetime, timedelta
from itertools import chain
from typing import Sequence

from common.utils import retry_on_serialization_error
from currencies.models import (
    AdjustmentTransaction,
    ExchangeTransaction,
    TransferTransaction,
)
from django.db import transaction
from django.db.models import F, Q, Sum
from django.utils import timezone


class TransactionsService:

    @classmethod
    def collapse_old_transactions(cls, *, old_than_timedelta: timedelta, service_names: Sequence[str]):
        now = timezone.now()
        cutoff_date = now - old_than_timedelta

        # Cуммы для AdjustmentTransaction
        adjustment_sums = (
            AdjustmentTransaction.objects.filter(
                created_at__lt=cutoff_date, status="CONFIRMED", service__name__in=service_names
            )
            .values("checking_account", "service")
            .annotate(total_amount=Sum("amount"))
        )

        # Cуммы для TransferTransaction (входящие и исходящие)
        transfer_sums_in = (
            TransferTransaction.objects.filter(
                created_at__lt=cutoff_date, status="CONFIRMED", service__name__in=service_names
            )
            .values("service", checking_account=F("to_checking_account"))
            .annotate(total_amount=Sum("to_amount"))
        )

        transfer_sums_out = (
            TransferTransaction.objects.filter(
                created_at__lt=cutoff_date, status="CONFIRMED", service__name__in=service_names
            )
            .values("service", checking_account=F("from_checking_account"))
            .annotate(total_amount=Sum("from_amount") * -1)  # Учитываем исходящие транзакции как отрицательные
        )

        # Cуммы для ExchangeTransaction (входящие и исходящие)
        exchange_sums_in = (
            ExchangeTransaction.objects.filter(
                created_at__lt=cutoff_date, status="CONFIRMED", service__name__in=service_names
            )
            .values("service", checking_account=F("to_checking_account"))
            .annotate(total_amount=Sum("to_amount"))
        )

        exchange_sums_out = (
            ExchangeTransaction.objects.filter(
                created_at__lt=cutoff_date, status="CONFIRMED", service__name__in=service_names
            )
            .values("service", checking_account=F("from_checking_account"))
            .annotate(total_amount=Sum("from_amount") * -1)  # Учитываем исходящие транзакции как отрицательные
        )

        # для хранения итоговых сумм по каждому аккаунту для каждого сервиса
        total_amounts = defaultdict(lambda: defaultdict(int))

        for item in chain(adjustment_sums, transfer_sums_in, transfer_sums_out, exchange_sums_in, exchange_sums_out):
            total_amounts[item["service"]][item["checking_account"]] += item["total_amount"]

        for service, accounts_with_total_amounts in total_amounts.items():
            cls._create_fake_transaction_and_remove_old(
                accounts_with_total_amounts=accounts_with_total_amounts,
                cutoff_date=cutoff_date,
                closed_date=now,
                service=service,
            )

    @classmethod
    @retry_on_serialization_error(max_retries=5)
    def _create_fake_transaction_and_remove_old(
        cls, *, accounts_with_total_amounts, cutoff_date: datetime, closed_date: datetime, service: str
    ):
        with transaction.atomic():
            # Создаем AdjustmentTransaction для каждого аккаунта
            # Удаляем старые транзакции

            AdjustmentTransaction.objects.filter(
                ~Q(status="PENDING"), created_at__lt=cutoff_date, service=service
            ).delete()
            TransferTransaction.objects.filter(
                ~Q(status="PENDING"), created_at__lt=cutoff_date, service=service
            ).delete()
            ExchangeTransaction.objects.filter(
                ~Q(status="PENDING"), created_at__lt=cutoff_date, service=service
            ).delete()

            for account_id, total_amount in accounts_with_total_amounts.items():
                adjustment_transaction = AdjustmentTransaction.objects.create(
                    description="The amount of old collapsed transactions",
                    service_id=service,
                    status="CONFIRMED",
                    status_description="Confirmed without real change amount in checking account",
                    auto_reject_after=closed_date,
                    created_at=cutoff_date,
                    closed_at=closed_date,
                    checking_account_id=account_id,
                    amount=total_amount,
                )
                adjustment_transaction.created_at = cutoff_date
                adjustment_transaction.save()
