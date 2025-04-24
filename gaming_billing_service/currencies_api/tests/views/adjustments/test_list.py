from decimal import Decimal
from typing import TYPE_CHECKING

from currencies.models import CurrencyService
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from currencies_api.utils import assemble_auth_headers
from django.test import TestCase, override_settings
from django.urls import reverse

if TYPE_CHECKING:
    from currencies.models import CurrencyUnit, Holder


@override_settings(ENABLE_HMAC_VALIDATION=False)
class AdjustmentListAPITest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesService.get_default()
        cls.service.enabled = True
        cls.service.permissions = {"root": True}
        cls.service.save()

        cls.service_auth = CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holder: Holder = HoldersTestFactory()
        cls.unit: CurrencyUnit = CurrencyUnitsTestFactory()

        cls.account = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit)

        for i in range(1, 11):
            AdjustmentsService.create(
                service=cls.service, checking_account=cls.account, amount=i, description=f"test_{i}"
            )

        cls.list_reverse_path = reverse("adjustments_list")

    def create_service_with_permissions(self, *, permissions: dict):
        service = CurrencyService.objects.create(
            name="test_name",
            enabled=True,
            permissions=permissions,
        )

        CurrencyServiceAuthTestFactory(service=service)

        return service

    def test_valid_get(self):
        response = self.client.get(
            self.list_reverse_path,
            data=dict(
                limit=1,
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(data["results"][0]["amount"]), 1, data)

    def test_valid_get_list(self):
        response = self.client.get(
            self.list_reverse_path,
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data["results"]), 10)

    def test_get_without_permissions(self):
        service = self.create_service_with_permissions(permissions={})

        response = self.client.get(
            self.list_reverse_path,
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission", data["message"])
