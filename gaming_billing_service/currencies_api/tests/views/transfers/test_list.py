from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import TransferRule
from currencies.services.accounts import AccountsService
from currencies.services.adjustments import AdjustmentsService
from currencies.services.transfers import TransfersService
from currencies.test_factories.currency_services import CurrencyServicesTestFactory
from currencies.test_factories.holders import HoldersTestFactory
from currencies.test_factories.units import CurrencyUnitsTestFactory
from currencies_api.test_factories.currency_service_auth import (
    CurrencyServiceAuthTestFactory,
)
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class TransfersListAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()

        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder_1 = HoldersTestFactory()
        cls.holder_2 = HoldersTestFactory()

        cls.unit_1 = CurrencyUnitsTestFactory()

        cls.account_1 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_1)[0]
        cls.account_2 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_1)[0]

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=cls.service,
                checking_account=cls.account_1,
                amount=1000,
                description="",
            ),
            status_description="",
        )

        cls.transfer_rule = TransferRule.objects.create(
            enabled=True,
            name="test_tranfer_rule_1",
            unit=cls.unit_1,
            fee_percent=Decimal("0"),
            min_from_amount=Decimal("0"),
        )

        cls.transfers = [
            TransfersService.create(
                service=cls.service,
                transfer_rule=cls.transfer_rule,
                from_checking_account=cls.account_1,
                to_checking_account=cls.account_2,
                from_amount=100,
                description="",
            )
            for _ in range(5)
        ]

        cls.list_reverse_path = reverse("transfers_list")

    def test_list_valid(self):
        response = self.client.get(
            self.list_reverse_path, data=dict(limit=4), headers=assemble_auth_headers(service=self.service)
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data.get("results")), 4)

    def test_list_enforce_access_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.list_reverse_path, data=dict(limit=4), headers=assemble_auth_headers(service=service)
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission 'transfers'", data.get("message"))
