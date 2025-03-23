from celery import shared_task
from currencies.services import ExchangesService, TransfersService

from .services import TransactionsService


@shared_task
def reject_outdated_currency_transactions():

    rejecteds = TransactionsService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def rejecting_outdated_transfer_transactions():

    rejecteds = TransfersService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def reject_outdated_exchange_transactions():

    rejecteds = ExchangesService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]
