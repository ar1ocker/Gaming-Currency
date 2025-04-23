from decimal import Decimal

from currencies.models import ExchangeRule
from currencies.services import AccountsService, AdjustmentsService, ExchangesService
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class ExchangesCreateAPITest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()

        cls.service_auth = CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder = HoldersTestFactory()
        cls.unit_1 = CurrencyUnitsTestFactory()
        cls.unit_2 = CurrencyUnitsTestFactory()

        cls.account_unit_1 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_1)
        cls.account_unit_2 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit_2)

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

        cls.create_reverse_path = reverse("exchanges_create")

        cls.headers = {settings.SERVICE_HEADER: cls.service.name}

    def test_valid_create(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                exchange_rule=self.exchange_rule.name,
                from_unit=self.unit_1.symbol,
                to_unit=self.unit_2.symbol,
                from_amount=5,
                description="test",
            ),
            headers=self.headers,
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201, data)
        self.assertIsNotNone(data.get("uuid"), data)
        self.assertEqual(data.get("status"), "PENDING", data)
        self.assertEqual(Decimal(data.get("from_amount")), Decimal("5"))

        self.assertEqual(ExchangesService.list().count(), 1)

    def test_enforce_create(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "exchanges": {
                    "enabled": True,
                    "create": {
                        "enabled": False,
                        "min_amount": 0,
                        "max_amount": 100,
                        "min_auto_reject": 0,
                        "max_auto_reject": 1000,
                    },
                }
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                exchange_rule=self.exchange_rule.name,
                from_unit=self.unit_1.symbol,
                to_unit=self.unit_2.symbol,
                from_amount=5,
                description="test",
            ),
            headers={settings.SERVICE_HEADER: service.name},
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Creating is disabled", data.get("message"))

    def test_enforce_auto_reject_timeout(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "exchanges": {
                    "enabled": True,
                    "create": {
                        "enabled": True,
                        "min_amount": 0,
                        "max_amount": 100,
                        "min_auto_reject": 0,
                        "max_auto_reject": 1,
                    },
                }
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                exchange_rule=self.exchange_rule.name,
                from_unit=self.unit_1.symbol,
                to_unit=self.unit_2.symbol,
                from_amount=5,
                description="test",
                auto_reject_timeout=100,
            ),
            headers={settings.SERVICE_HEADER: service.name},
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Auto reject timeout is out of range", data.get("message"))

    def test_enforce_amount(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "exchanges": {
                    "enabled": True,
                    "create": {
                        "enabled": True,
                        "min_amount": 0,
                        "max_amount": 1,
                        "min_auto_reject": 0,
                        "max_auto_reject": 1000,
                    },
                }
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                exchange_rule=self.exchange_rule.name,
                from_unit=self.unit_1.symbol,
                to_unit=self.unit_2.symbol,
                from_amount=5,
                description="test",
                auto_reject_timeout=100,
            ),
            headers={settings.SERVICE_HEADER: service.name},
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Amount is out of range", data.get("message"))
