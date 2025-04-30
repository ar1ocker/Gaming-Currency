from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import TransferRule
from currencies.services import AccountsService, AdjustmentsService, TransfersService
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class TransfersCreateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder_1 = HoldersTestFactory()
        cls.holder_2 = HoldersTestFactory()

        cls.unit_1 = CurrencyUnitsTestFactory()

        cls.account_holder_1 = AccountsService.get_or_create(holder=cls.holder_1, currency_unit=cls.unit_1)[0]
        cls.account_holder_2 = AccountsService.get_or_create(holder=cls.holder_2, currency_unit=cls.unit_1)[0]

        cls.transfer_rule = TransferRule.objects.create(
            enabled=True,
            name="test_tranfer_rule_1",
            unit=cls.unit_1,
            fee_percent=Decimal("0"),
            min_from_amount=Decimal("0"),
        )

        AdjustmentsService.confirm(
            adjustment_transaction=AdjustmentsService.create(
                service=cls.service, checking_account=cls.account_holder_1, amount=1000, description=""
            ),
            status_description="",
        )

        cls.create_reverse_path = reverse("transfers_create")

    def test_valid(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                from_holder_id=self.holder_1.holder_id,
                to_holder_id=self.holder_2.holder_id,
                transfer_rule=self.transfer_rule.name,
                amount=10,
                description="test",
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201, data)
        self.assertEqual(data.get("status"), "PENDING")
        self.assertIsNotNone(data.get("uuid"))

        self.assertEqual(TransfersService.list().count(), 1)

    def test_enforce_create_permissions(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "transfers": {
                    "enabled": True,
                    "create": {
                        "enabled": False,
                        "max_auto_reject": 1000,
                        "min_auto_reject": 0,
                        "min_amount": 0,
                        "max_amount": 1000,
                    },
                },
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                from_holder_id=self.holder_1.holder_id,
                to_holder_id=self.holder_2.holder_id,
                transfer_rule=self.transfer_rule.name,
                amount=10,
                description="test",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Creating is disabled", data.get("message"), data)

    def test_enforce_auto_reject_timeout_permissions(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "transfers": {
                    "enabled": True,
                    "create": {
                        "enabled": True,
                        "max_auto_reject": 1,
                        "min_auto_reject": 0,
                        "min_amount": 0,
                        "max_amount": 1000,
                    },
                },
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                from_holder_id=self.holder_1.holder_id,
                to_holder_id=self.holder_2.holder_id,
                transfer_rule=self.transfer_rule.name,
                amount=10,
                description="test",
                auto_reject_timeout=100,
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Auto reject timeout is out of range", data.get("message"), data)
