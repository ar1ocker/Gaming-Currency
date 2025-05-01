from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import TransferRule
from currencies.services.accounts import AccountsService
from currencies.services.adjustments import AdjustmentsService
from currencies.services.transfers import TransfersService
from currencies.test_factories import CurrencyServicesTestFactory
from currencies.test_factories.holders import HoldersTestFactory
from currencies.test_factories.units import CurrencyUnitsTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class TransfersRejectAPITests(TestCase):
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

        cls.transfer = TransfersService.create(
            service=cls.service,
            transfer_rule=cls.transfer_rule,
            from_checking_account=cls.account_holder_1,
            to_checking_account=cls.account_holder_2,
            from_amount=100,
            description="",
        )

        cls.reject_reverse_path = reverse("transfers_reject")

    def test_valid(self):
        response = self.client.post(
            self.reject_reverse_path,
            data=dict(uuid=self.transfer.uuid, status_description="test status descr"),
            headers=assemble_auth_headers(service=self.service),
        )

        self.assertEqual(response.status_code, 200)

        self.transfer.refresh_from_db()

        self.assertEqual(self.transfer.status, "REJECTED")
        self.assertEqual(self.transfer.status_description, "test status descr")

    def test_enforce_reject_permission(self):
        service = CurrencyServicesTestFactory(
            permissions={
                "transfers": {
                    "enabled": True,
                    "reject": {
                        "enabled": False,
                        "services": [self.service.name],
                    },
                },
            }
        )

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(uuid=self.transfer.uuid, status_description="test status descr"),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Reject is disabled", data.get("message"))

        self.transfer.refresh_from_db()
        self.assertEqual(self.transfer.status, "PENDING")
