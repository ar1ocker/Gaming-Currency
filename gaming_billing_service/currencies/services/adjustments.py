import logging
from datetime import timedelta

from currencies.models import AdjustmentTransaction, CheckingAccount, Service
from currencies.utils import retry_on_serialization_error
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone


class AdjustmentsService:
    ValidationError = ValidationError

    @classmethod
    @retry_on_serialization_error()
    def create(
        cls,
        *,
        service: Service,
        checking_account: CheckingAccount,
        amount: int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEOUT,
    ) -> AdjustmentTransaction:
        with transaction.atomic():
            blocked_checking_account = CheckingAccount.objects.get(pk=checking_account.pk)

            # Когда мы тратим валюту (amount < 0) - выводим валюту со счета сразу, чтобы заблокировать её трату до
            # подтверждения транзакции или же вернуть её при отмене транзакции
            if amount < 0:
                abs_amount = abs(amount)

                if blocked_checking_account.amount < abs_amount:
                    raise ValidationError("Insufficient funds in the checking account")

                blocked_checking_account.amount = F("amount") - abs_amount
                blocked_checking_account.save()

            currency_transaction = AdjustmentTransaction(
                service=service,
                checking_account=blocked_checking_account,
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
            blocked_currency_transaction = AdjustmentTransaction.objects.select_related("checking_account").get(
                pk=adjustment_transaction.pk
            )

            blocked_currency_transaction._confirm(status_description)

            # Когда мы добавляем валюту на счет - мы добавляем её только при подтвержденном статусе транзакции
            if blocked_currency_transaction.amount > 0:
                blocked_currency_transaction.checking_account.amount = F("amount") + blocked_currency_transaction.amount
                blocked_currency_transaction.checking_account.save()

        return blocked_currency_transaction

    @classmethod
    @retry_on_serialization_error()
    def reject(cls, *, adjustment_transaction: AdjustmentTransaction, status_description: str):
        with transaction.atomic():
            blocked_currency_transaction = AdjustmentTransaction.objects.select_related("checking_account").get(
                pk=adjustment_transaction.pk
            )

            blocked_currency_transaction._reject(status_description)

            # Возвращаем валюту которая была заблокирована при создании транзакции
            if blocked_currency_transaction.amount < 0:
                blocked_currency_transaction.checking_account.amount = F("amount") + abs(
                    blocked_currency_transaction.amount
                )
                blocked_currency_transaction.checking_account.save()

        return blocked_currency_transaction

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
