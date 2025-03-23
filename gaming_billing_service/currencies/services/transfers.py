import logging
from datetime import timedelta

from currencies.models import CheckingAccount, Service, TransferTransaction
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
        from_checking_account: CheckingAccount,
        to_checking_account: CheckingAccount,
        amount: int,
        description: str,
        auto_reject_timedelta: timedelta = settings.DEFAULT_AUTO_REJECT_TIMEOUT,
    ) -> TransferTransaction:
        if from_checking_account == to_checking_account:
            raise ValidationError("Transfer to between the same account")

        if from_checking_account.currency_unit != to_checking_account.currency_unit:
            raise ValidationError("Transfer with different currency units")

        with transaction.atomic():
            blocked_from_checking_account = CheckingAccount.objects.get(pk=from_checking_account.pk)

            if blocked_from_checking_account.amount < amount:
                raise ValidationError("Insufficient funds in the checking account")

            blocked_from_checking_account.amount = F("amount") - amount
            blocked_from_checking_account.save()

            transfer_transaction = TransferTransaction(
                service=service,
                from_checking_account=from_checking_account,
                to_checking_account=to_checking_account,
                amount=amount,
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
            to_checking_account.amount = F("amount") + blocked_transfer_transaction.amount

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
            from_checking_account.amount = F("amount") + blocked_transfer_transaction.amount

            from_checking_account.save()

        return blocked_transfer_transaction

    @classmethod
    def reject_all_outdated(cls, *, status_description="Rejected as outdated") -> list[TransferTransaction]:
        now = timezone.now()

        transactions = TransferTransaction.objects.filter(status="PENDING", auto_reject_after__lt=now)

        rejected = []
        for transaction in transactions:
            try:
                rejected.append(cls.reject(transfer_transaction=transaction, status_description=status_description))
            except cls.ValidationError as e:
                logging.error(
                    f"Error on rejecting outdated transfer transactions, transaction {transaction.uuid}, error {str(e)}"
                )

            # TODO Ошибки сериализации?

        return rejected
