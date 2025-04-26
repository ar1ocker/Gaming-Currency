from itertools import chain
from typing import Any

from currencies.models import ExchangeRule, TransferRule
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    ExchangesService,
    HoldersTypeService,
    TransfersService,
)
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
    HoldersTypeTestFactory,
)
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "Создаёт тестовые данные"

    def handle(self, *args: Any, **options: Any) -> str | None:
        with transaction.atomic():
            service = CurrencyServicesTestFactory()

            units = [CurrencyUnitsTestFactory(precision=i) for i in range(1, 5)]

            holder_type_1 = HoldersTypeService.get_default()
            holder_type_2 = HoldersTypeTestFactory()

            holders = [HoldersTestFactory(holder_type=holder_type_1) for _ in range(20)]
            holders.extend([HoldersTestFactory(holder_type=holder_type_2) for _ in range(20)])

            accounts_unit_1 = []
            for holder in holders:
                accounts_unit_1.append(AccountsService.get_or_create(holder=holder, currency_unit=units[0])[0])

            accounts_unit_2 = []
            for holder in holders:
                accounts_unit_2.append(AccountsService.get_or_create(holder=holder, currency_unit=units[3])[0])

            for account in chain(accounts_unit_1, accounts_unit_2):
                AdjustmentsService.create(
                    service=service, checking_account=account, amount=1000, description="Pending adjustment"
                )
                AdjustmentsService.confirm(
                    adjustment_transaction=AdjustmentsService.create(
                        service=service, checking_account=account, amount=2000, description="Confirmed adjustment"
                    ),
                    status_description="Confirmed by test data creation",
                )
                AdjustmentsService.reject(
                    adjustment_transaction=AdjustmentsService.create(
                        service=service, checking_account=account, amount=200, description="Rejected adjustment"
                    ),
                    status_description="Rejected by test data creation",
                )

                AdjustmentsService.confirm(
                    adjustment_transaction=AdjustmentsService.create(
                        service=service, checking_account=account, amount=-10, description="Confirmed adjustment"
                    ),
                    status_description="Confirmed by test data creation",
                )

            exchange_rule = ExchangeRule(
                enabled_forward=True,
                enabled_reverse=True,
                name="exchange_rule",
                first_unit=units[0],
                second_unit=units[3],
                forward_rate=100,
                reverse_rate=80,
                min_first_amount=10,
                min_second_amount=1,
            )

            exchange_rule.full_clean()
            exchange_rule.save()

            for account_1, account_2 in zip(accounts_unit_1, accounts_unit_2):
                ExchangesService.create(
                    service=service,
                    holder=account_1.holder,
                    exchange_rule=exchange_rule,
                    from_unit=account_1.currency_unit,
                    to_unit=account_2.currency_unit,
                    from_amount=100,
                    description="Pending exchange",
                )
                ExchangesService.confirm(
                    exchange_transaction=ExchangesService.create(
                        service=service,
                        holder=account_1.holder,
                        exchange_rule=exchange_rule,
                        from_unit=account_1.currency_unit,
                        to_unit=account_2.currency_unit,
                        from_amount=100,
                        description="Confirmed exchange",
                    ),
                    status_description="Confirmed exchange",
                )

                ExchangesService.reject(
                    exchange_transaction=ExchangesService.create(
                        service=service,
                        holder=account_1.holder,
                        exchange_rule=exchange_rule,
                        from_unit=account_1.currency_unit,
                        to_unit=account_2.currency_unit,
                        from_amount=100,
                        description="Rejected exchange",
                    ),
                    status_description="Rejected exchange",
                )

            transfer_rule = TransferRule(
                enabled=True, name="transfer rule 1", unit=units[3], fee_percent=10, min_from_amount=10
            )

            transfer_rule.full_clean()
            transfer_rule.save()

            for account_1, account_2 in zip(accounts_unit_2[:10], accounts_unit_2[10:]):
                TransfersService.create(
                    service=service,
                    transfer_rule=transfer_rule,
                    from_checking_account=account_1,
                    to_checking_account=account_2,
                    from_amount=100,
                    description="Pending transfer",
                )
                TransfersService.confirm(
                    transfer_transaction=TransfersService.create(
                        service=service,
                        transfer_rule=transfer_rule,
                        from_checking_account=account_1,
                        to_checking_account=account_2,
                        from_amount=100,
                        description="Confirmed transfer",
                    ),
                    status_description="Confirmed transfer",
                )
                TransfersService.reject(
                    transfer_transaction=TransfersService.create(
                        service=service,
                        transfer_rule=transfer_rule,
                        from_checking_account=account_1,
                        to_checking_account=account_2,
                        from_amount=100,
                        description="Rejected transfer",
                    ),
                    status_description="Rejected transfer",
                )
