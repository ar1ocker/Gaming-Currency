from celery import shared_task
from currencies.services import (
    AdjustmentsService,
    ExchangesService,
    TransactionsService,
    TransfersService,
)
from django.conf import settings


@shared_task
def reject_outdated_currency_transactions():

    rejecteds = AdjustmentsService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def rejecting_outdated_transfer_transactions():

    rejecteds = TransfersService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def reject_outdated_exchange_transactions():

    rejecteds = ExchangesService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def collapse_all_old_transactions():
    TransactionsService.collapse_old_transactions(old_than_timedelta=settings.COLLAPSE_OLD_TRANSACTIONS_TIMEDELTA)
