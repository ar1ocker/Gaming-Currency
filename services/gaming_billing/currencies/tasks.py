from datetime import timedelta
from typing import Sequence

from celery import shared_task
from currencies.services import (
    AdjustmentsService,
    ExchangesService,
    TransactionsService,
    TransfersService,
)


@shared_task
def reject_outdated_adjustments():

    rejecteds = AdjustmentsService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def rejecting_outdated_transfers():

    rejecteds = TransfersService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def reject_outdated_exchanges():

    rejecteds = ExchangesService.reject_all_outdated(status_description="Rejected by cron as outdated")

    return [str(i.uuid) for i in rejecteds]


@shared_task
def collapse_all_old_transactions(*, older_than_days: int, service_names: Sequence[str]):
    TransactionsService.collapse_old_transactions(
        old_than_timedelta=timedelta(days=older_than_days), service_names=service_names
    )
