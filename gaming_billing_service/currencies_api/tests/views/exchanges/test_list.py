from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import ExchangeRule
from currencies.services import ExchangesService
from currencies.services.accounts import AccountsService
from currencies.services.adjustments import AdjustmentsService
from currencies.test_factories import CurrencyServicesTestFactory
from currencies.test_factories.holders import HoldersTestFactory
from currencies.test_factories.units import CurrencyUnitsTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase
from django.urls import reverse


class ExhcnagesListAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder = HoldersTestFactory()

        cls.unit_1 = CurrencyUnitsTestFactory()
        cls.unit_2 = CurrencyUnitsTestFactory()

        cls.account_1 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_1)
        AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_2)

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=cls.service, checking_account=cls.account_1, amount=1000, description=""
            ),
            status_description="",
        )

        cls.exchange_rule = ExchangeRule.objects.create(
            enabled_forward=True,
            enabled_reverse=True,
            name="exchange rule name",
            first_unit=cls.unit_1,
            second_unit=cls.unit_2,
            forward_rate=Decimal(10),
            reverse_rate=Decimal(1),
            min_first_amount=Decimal(1),
            min_second_amount=Decimal(1),
        )

        cls.exchanges = [
            ExchangesService.create(
                service=cls.service,
                holder=cls.holder,
                exchange_rule=cls.exchange_rule,
                from_unit=cls.unit_1,
                to_unit=cls.unit_2,
                from_amount=Decimal(100),
                description="",
            )
            for _ in range(3)
        ]

        cls.list_reverse_path = reverse("exchanges_list")

    def test_list_valid(self):
        response = self.client.get(self.list_reverse_path, headers=assemble_auth_headers(service=self.service))

        self.assertEqual(response.status_code, 200)

        data = response.data  # type: ignore

        self.assertEqual(len(data.get("results")), 3)

    def test_list_without_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(self.list_reverse_path, headers=assemble_auth_headers(service=service))

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission", data.get("message"))
