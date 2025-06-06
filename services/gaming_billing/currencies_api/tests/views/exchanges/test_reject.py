from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import ExchangeRule
from currencies.services import AccountsService, AdjustmentsService, ExchangesService
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class ExchangesRejectAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()

        cls.service_auth = CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder = HoldersTestFactory()
        cls.unit_1 = CurrencyUnitsTestFactory()
        cls.unit_2 = CurrencyUnitsTestFactory()

        cls.account_unit_1 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_1)[0]
        cls.account_unit_2 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_2)[0]

        cls.exchange_rule = ExchangeRule.objects.create(
            name="exchange_rule",
            enabled_forward=True,
            enabled_reverse=True,
            first_unit=cls.unit_1,
            second_unit=cls.unit_2,
            forward_rate=Decimal(10),
            reverse_rate=Decimal(5),
            min_first_amount=Decimal(1),
            min_second_amount=Decimal(1),
        )

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=cls.service, checking_account=cls.account_unit_1, amount=1000, description=""
            ),
            status_description="",
        )
        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=cls.service, checking_account=cls.account_unit_2, amount=1000, description=""
            ),
            status_description="",
        )

        cls.exchange = ExchangesService.create(
            service=cls.service,
            holder=cls.holder,
            exchange_rule=cls.exchange_rule,
            from_unit=cls.unit_1,
            to_unit=cls.unit_2,
            from_amount=Decimal(10),
            description="",
        )

        cls.reject_reverse_path = reverse("exchanges_reject")

        cls.headers = assemble_auth_headers(service=cls.service)

    def test_reject_valid(self):
        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.exchange.uuid,
                status_description="description for status",
            ),
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 200)

        self.exchange.refresh_from_db()
        self.assertEqual(self.exchange.status, "REJECTED")
        self.assertEqual(self.exchange.status_description, "description for status")

    def test_enforce_reject(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "exchanges": {
                    "enabled": True,
                    "reject": {"enabled": False, "services": [self.service.name]},
                }
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.exchange.uuid,
                status_description="description for status",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Reject is disabled", data.get("message"))
