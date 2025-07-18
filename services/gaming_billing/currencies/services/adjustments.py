import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

import django_filters
from common.utils import get_decimal_places, retry_on_serialization_error
from currencies.models import AdjustmentTransaction, CheckingAccount, CurrencyService
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, QuerySet
from django.utils import timezone


class AdjustmentsService:
    ValidationError = ValidationError

    @classmethod
    @retry_on_serialization_error()
    def create(
        cls,
        *,
        service: CurrencyService,
        checking_account: CheckingAccount,
        amount: Decimal | int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEDELTA,
    ) -> AdjustmentTransaction:
        if isinstance(amount, int):
            amount = Decimal(amount)
        else:
            amount = amount.normalize()

        if amount == 0:
            raise ValidationError({"amount": "The amount cannot be zero"})

        if get_decimal_places(amount) > checking_account.currency_unit.precision:
            raise ValidationError(
                f"Число знаков после запятой у валюты больше чем возможно: {amount},"
                f" максимальная точность {checking_account.currency_unit.precision}"
            )

        with transaction.atomic():
            # Когда мы тратим валюту (amount < 0) - выводим валюту со счета сразу, чтобы заблокировать её трату до
            # подтверждения транзакции или же вернуть её при отмене транзакции

            abs_amount = abs(amount)

            if amount < 0:
                if checking_account.currency_unit.is_negative_allowed:
                    CheckingAccount.objects.filter(pk=checking_account.pk).update(amount=F("amount") - abs_amount)
                else:
                    updated = CheckingAccount.objects.filter(pk=checking_account.pk, amount__gte=abs_amount).update(
                        amount=F("amount") - abs_amount
                    )

                    if not updated:
                        raise ValidationError("Insufficient funds in the checking account")

                checking_account.refresh_from_db(fields=["amount", "updated_at"])

            currency_transaction = AdjustmentTransaction(
                service=service,
                checking_account=checking_account,
                amount=amount,
                description=description,
                auto_reject_after=timezone.now() + auto_reject_timedelta,
            )

            currency_transaction.full_clean()
            currency_transaction.save()

        return currency_transaction

    @classmethod
    @retry_on_serialization_error()
    def confirm(cls, *, adjustment_transaction: AdjustmentTransaction, status_description: str):
        with transaction.atomic():
            adjustment_transaction._confirm(status_description)

            # Когда мы добавляем валюту на счет - мы добавляем её только при подтвержденном статусе транзакции
            if adjustment_transaction.amount > 0:
                adjustment_transaction.checking_account.amount = F("amount") + adjustment_transaction.amount
                adjustment_transaction.checking_account.save(update_fields=["amount", "updated_at"])
                adjustment_transaction.checking_account.refresh_from_db(fields=["amount", "updated_at"])

        return adjustment_transaction

    @classmethod
    @retry_on_serialization_error()
    def reject(cls, *, adjustment_transaction: AdjustmentTransaction, status_description: str):
        with transaction.atomic():

            adjustment_transaction._reject(status_description)

            # Возвращаем валюту которая была заблокирована при создании транзакции
            if adjustment_transaction.amount < 0:
                adjustment_transaction.checking_account.amount = F("amount") + abs(adjustment_transaction.amount)
                adjustment_transaction.checking_account.save(update_fields=["amount", "updated_at"])
                adjustment_transaction.checking_account.refresh_from_db(fields=["amount", "updated_at"])

        return adjustment_transaction

    @classmethod
    def reject_all_outdated(cls, *, status_description="Rejected as outdated") -> list[AdjustmentTransaction]:
        now = timezone.now()

        transactions = AdjustmentTransaction.objects.filter(status="PENDING", auto_reject_after__lt=now)

        rejected = []
        for adjustment in transactions:
            try:
                rejected.append(cls.reject(adjustment_transaction=adjustment, status_description=status_description))
            except cls.ValidationError as e:
                logging.error(
                    f"Error on rejecting outdated transfer transactions, transaction {adjustment.uuid}, error {str(e)}"
                )

            # TODO Ошибки сериализации?

        return rejected

    @classmethod
    def list(cls, *, filters: dict[str, Any] | None = None) -> QuerySet[AdjustmentTransaction]:
        filters = filters or {}

        queryset = AdjustmentTransaction.objects.all()

        return AdjustmentsFilter(data=filters, queryset=queryset).qs


class AdjustmentsFilter(django_filters.FilterSet):
    service = django_filters.CharFilter(field_name="service__name")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    holder = django_filters.CharFilter(field_name="checking_account__holder__holder_id")
    currency_unit = django_filters.CharFilter(field_name="checking_account__currency_unit__symbol")
    amount = django_filters.RangeFilter()
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    closed_at = django_filters.IsoDateTimeFromToRangeFilter()

    ordering = django_filters.OrderingFilter(fields=["created_at", "closed_at", "amount"])

    class Meta:
        model = AdjustmentTransaction
        fields = ["service", "status", "holder", "currency_unit", "amount", "created_at", "closed_at"]
