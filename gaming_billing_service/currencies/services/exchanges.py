import logging
from datetime import timedelta
from decimal import Decimal

from currencies.models import (
    CurrencyService,
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
)
from currencies.utils import retry_on_serialization_error, get_decimal_places
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
import django_filters
from .accounts import AccountsService


class ExchangesService:
    ValidationError = ValidationError

    @classmethod
    @retry_on_serialization_error()
    def create(
        cls,
        *,
        service: CurrencyService,
        holder: Holder,
        exchange_rule: ExchangeRule,
        from_unit: CurrencyUnit,
        to_unit: CurrencyUnit,
        from_amount: Decimal | int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEDELTA,
    ):
        if isinstance(from_amount, int):
            from_amount = Decimal(from_amount)

        from_amount = from_amount.normalize()

        if from_unit not in exchange_rule.units:
            raise ValidationError("from_unit is not in units")

        if to_unit not in exchange_rule.units:
            raise ValidationError("to_unit is not in units")

        if exchange_rule.first_unit == from_unit:  # forward exchange
            is_forward_exchange = True
            rate = exchange_rule.forward_rate
            min_amount = exchange_rule.min_first_amount

            if not exchange_rule.enabled_forward:
                raise ValidationError("Forward exchange is disabled")

        else:
            is_forward_exchange = False
            rate = exchange_rule.reverse_rate
            min_amount = exchange_rule.min_second_amount

            if not exchange_rule.enabled_reverse:
                raise ValidationError("Reverse exchange is disabled")

        if get_decimal_places(from_amount) > from_unit.precision:
            raise ValidationError(
                f"Число знаков после запятой у снимаемой валюты больше чем возможно: {from_amount},"
                f" максимальная точность {from_unit.precision}"
            )

        if from_amount < min_amount:
            raise ValidationError("Списываемая сумма меньше минимальной {from_amount} < {min_amount}")

        if is_forward_exchange:
            to_amount = from_amount / rate
        else:
            to_amount = from_amount * rate

        if get_decimal_places(to_amount) > to_unit.precision:
            raise ValidationError(
                f"Число знаков после запятой у получаемой валюты больше чем возможно: {to_amount},"
                f" максимальная точность {to_unit.precision}"
            )

        with transaction.atomic():
            from_account = AccountsService.get(holder=holder, currency_unit=from_unit)
            to_account = AccountsService.get(holder=holder, currency_unit=to_unit)

            if from_account is None:
                raise ValidationError("From checking account not found")

            if to_account is None:
                raise ValidationError("To checking account not found")

            if from_account.amount < from_amount:
                raise ValidationError("Insufficient funds in the 'from' checking account")

            from_account.amount = F("amount") - from_amount
            from_account.save()

            exchange_transaction = ExchangeTransaction(
                service=service,
                description=description,
                auto_reject_after=timezone.now() + auto_reject_timedelta,
                exchange_rule=exchange_rule,
                from_checking_account=from_account,
                to_checking_account=to_account,
                from_amount=from_amount,
                to_amount=to_amount,
            )

            exchange_transaction.full_clean()
            exchange_transaction.save()

        return exchange_transaction

    @classmethod
    @retry_on_serialization_error()
    def confirm(cls, *, exchange_transaction: ExchangeTransaction, status_description: str):
        with transaction.atomic():
            blocked_exchange_transaction = ExchangeTransaction.objects.select_related("to_checking_account").get(
                pk=exchange_transaction.pk
            )

            blocked_exchange_transaction._confirm(status_description)

            to_checking_account = blocked_exchange_transaction.to_checking_account
            to_checking_account.amount = F("amount") + blocked_exchange_transaction.to_amount

            to_checking_account.save()

        return blocked_exchange_transaction

    @classmethod
    @retry_on_serialization_error()
    def reject(cls, *, exchange_transaction: ExchangeTransaction, status_description: str):
        with transaction.atomic():
            blocked_exchange_transaction = ExchangeTransaction.objects.select_related("from_checking_account").get(
                pk=exchange_transaction.pk
            )

            blocked_exchange_transaction._reject(status_description)

            from_checking_account = blocked_exchange_transaction.from_checking_account
            from_checking_account.amount = F("amount") + blocked_exchange_transaction.from_amount

            from_checking_account.save()

        return blocked_exchange_transaction

    @classmethod
    def reject_all_outdated(cls, *, status_description="Rejected as outdated") -> list[ExchangeTransaction]:
        now = timezone.now()

        transactions = ExchangeTransaction.objects.filter(status="PENDING", auto_reject_after__lt=now)

        rejected = []
        for exchange in transactions:
            try:
                rejected.append(cls.reject(exchange_transaction=exchange, status_description=status_description))
            except cls.ValidationError as e:
                logging.error(
                    f"Error on rejecting outdated transfer transactions, transaction {exchange.uuid}, error {str(e)}"
                )

            # TODO Ошибки сериализации?

        return rejected

    @classmethod
    def list(cls, *, filters: dict[str, str] | None = None):
        filters = filters or {}

        queryset = ExchangeTransaction.objects.all()

        return ExchangesFilter(data=filters, queryset=queryset).qs


class ExchangesFilter(django_filters.FilterSet):
    service = django_filters.CharFilter(field_name="service__name")
    status = django_filters.CharFilter(field_name="status", lookup_expr="iexact")
    holder = django_filters.CharFilter(field_name="from_checking_account__holder__holder_id")
    created_at = django_filters.IsoDateTimeFromToRangeFilter()
    closed_at = django_filters.IsoDateTimeFromToRangeFilter()

    exchange_rule = django_filters.CharFilter(field_name="exchange_rule__name")

    from_amount = django_filters.RangeFilter()
    to_amount = django_filters.RangeFilter()
    from_unit = django_filters.CharFilter(field_name="from_checking_account__currency_unit__symbol")
    to_unit = django_filters.CharFilter(field_name="to_checking_account__currency_unit__symbol")

    class Meta:
        model = ExchangeTransaction
        fields = [
            "service",
            "status",
            "created_at",
            "closed_at",
            "exchange_rule",
            "from_checking_account",
            "to_checking_account",
            "from_amount",
            "to_amount",
        ]
