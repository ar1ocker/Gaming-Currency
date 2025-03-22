from datetime import timedelta

from currencies.models import (
    CurrencyUnit,
    ExchangeRule,
    ExchangeTransaction,
    Holder,
    Service,
)
from currencies.utils import retry_on_serialization_error
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .accounts import AccountsService


class ExchangesService:
    ValidationError = ValidationError

    @classmethod
    @retry_on_serialization_error()
    def create(
        cls,
        *,
        service: Service,
        holder: Holder,
        exchange_rule: ExchangeRule,
        from_unit: CurrencyUnit,
        to_unit: CurrencyUnit,
        from_amount: int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEOUT,
    ):
        if from_unit not in exchange_rule.units:
            raise ValidationError("from_unit is not in units")

        if to_unit not in exchange_rule.units:
            raise ValidationError("to_unit is not in units")

        if exchange_rule.first_unit == from_unit:
            is_forward_exchange = True
            rate = exchange_rule.forward_rate
            min_amount = exchange_rule.min_first_amount
        else:
            is_forward_exchange = False
            rate = exchange_rule.reverse_rate
            min_amount = exchange_rule.min_second_amount

        if from_amount < min_amount:
            raise ValidationError("Списываемая сумма меньше минимальной {from_amount} < {min_amount}")

        if is_forward_exchange:
            if not exchange_rule.enabled_forward:
                raise ValidationError("Forward exchange is disabled")

            if from_amount % rate != 0:
                raise ValidationError("Сумма не делится нацело (без остатка) на ставку {from_amount} % {rate} != 0")

        else:  # is reverse exchange
            if not exchange_rule.enabled_reverse:
                raise ValidationError("Reverse exchange is disabled")

        with transaction.atomic():
            from_account = AccountsService.get_or_create(holder=holder, currency_unit=from_unit)
            to_account = AccountsService.get_or_create(holder=holder, currency_unit=to_unit)

            if from_account.amount < from_amount:
                raise ValidationError("Insufficient funds in the 'from' checking account")

            from_account.amount = F("amount") - from_amount
            from_account.save()

            if is_forward_exchange:
                to_amount = from_amount // rate
            else:
                to_amount = from_amount * rate

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
