import logging
from datetime import timedelta
from decimal import Decimal

from currencies.models import (
    CheckingAccount,
    Service,
    TransferRule,
    TransferTransaction,
)
from currencies.utils import retry_on_serialization_error
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone


class TransfersService:
    ValidationError = ValidationError

    @classmethod
    @retry_on_serialization_error()
    def create(
        cls,
        *,
        service: Service,
        transfer_rule: TransferRule,
        from_checking_account: CheckingAccount,
        to_checking_account: CheckingAccount,
        from_amount: Decimal | int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEOUT,
    ) -> TransferTransaction:
        if not transfer_rule.enabled:
            raise ValidationError("Transfer is disabled")

        if isinstance(from_amount, Decimal):
            from_amount = from_amount.quantize(Decimal(".0000"))

        # calculate fee percent from to_amount
        to_amount = (from_amount - (from_amount * (transfer_rule.fee_percent / 100))).quantize(Decimal("0.0000"))

        if from_amount < transfer_rule.min_from_amount:
            raise ValidationError("from_amount < min_from_amount")

        if to_amount <= 0:
            raise ValidationError("from_amount is too small, to_amount <= 0")

        if from_checking_account == to_checking_account:
            raise ValidationError("Transfer to between the same account")

        if (
            transfer_rule.unit != from_checking_account.currency_unit
            or transfer_rule.unit != to_checking_account.currency_unit
        ):
            raise ValidationError("Transfer with unsuitable currency")

        with transaction.atomic():
            blocked_from_checking_account = CheckingAccount.objects.get(pk=from_checking_account.pk)

            if blocked_from_checking_account.amount < from_amount:
                raise ValidationError("Insufficient funds in the checking account")

            blocked_from_checking_account.amount = F("amount") - from_amount
            blocked_from_checking_account.save()

            transfer_transaction = TransferTransaction(
                service=service,
                transfer_rule=transfer_rule,
                from_checking_account=from_checking_account,
                to_checking_account=to_checking_account,
                from_amount=from_amount,
                to_amount=to_amount,
                description=description,
                auto_reject_after=timezone.now() + auto_reject_timedelta,
            )

            transfer_transaction.full_clean()
            transfer_transaction.save()

        return transfer_transaction

    @classmethod
    @retry_on_serialization_error()
    def confirm(cls, *, transfer_transaction: TransferTransaction, status_description: str):
        with transaction.atomic():
            blocked_transfer_transaction = TransferTransaction.objects.select_related("to_checking_account").get(
                pk=transfer_transaction.pk
            )

            blocked_transfer_transaction._confirm(status_description)

            # Передаём валюту получателю
            to_checking_account = blocked_transfer_transaction.to_checking_account
            to_checking_account.amount = F("amount") + blocked_transfer_transaction.to_amount

            to_checking_account.save()

        return blocked_transfer_transaction

    @classmethod
    @retry_on_serialization_error()
    def reject(cls, *, transfer_transaction: TransferTransaction, status_description: str):
        with transaction.atomic():
            blocked_transfer_transaction = TransferTransaction.objects.select_related("from_checking_account").get(
                pk=transfer_transaction.pk
            )

            blocked_transfer_transaction._reject(status_description)

            # Возвращаем валюту отправителю
            from_checking_account = blocked_transfer_transaction.from_checking_account
            from_checking_account.amount = F("amount") + blocked_transfer_transaction.from_amount

            from_checking_account.save()

        return blocked_transfer_transaction

    @classmethod
    def reject_all_outdated(cls, *, status_description="Rejected as outdated") -> list[TransferTransaction]:
        now = timezone.now()

        transactions = TransferTransaction.objects.filter(status="PENDING", auto_reject_after__lt=now)

        rejected = []
        for transfer in transactions:
            try:
                rejected.append(cls.reject(transfer_transaction=transfer, status_description=status_description))
            except cls.ValidationError as e:
                logging.error(
                    f"Error on rejecting outdated transfer transactions, transaction {transfer.uuid}, error {str(e)}"
                )

            # TODO Ошибки сериализации?

        return rejected
