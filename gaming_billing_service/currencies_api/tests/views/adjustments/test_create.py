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
class AdjustmentCreateAPITest(TestCase):
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

        cls.create_reverse_path = reverse("adjustments_create")

        cls.headers = assemble_auth_headers(service=cls.service)

    def create_service_with_permissions(self, *, permissions: dict):
        service = CurrencyService.objects.create(
            name="test_name",
            enabled=True,
            permissions=permissions,
        )

        CurrencyServiceAuthTestFactory(service=service)

        return service

    def test_valid_create(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=self.headers,
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 201, data)
        self.assertIsNotNone(data.get("uuid"), data)
        self.assertEqual(data.get("status"), "PENDING", data)
        self.assertEqual(Decimal(data.get("amount")), Decimal(100), data)  # type: ignore

        self.assertEqual(AdjustmentsService.list().count(), 1)

    def test_holder_not_found(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id="undefined holder_id",
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=self.headers,
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 400, data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_unit_not_found(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol="randon unit",
                amount=100,
                description="test_description",
            ),
            headers=self.headers,
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 400, data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_reject_timeout_less_zero(self):
        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
                auto_reject_timeout=-100,
            ),
            headers=self.headers,
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 400, data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_access_permission_pass(self):
        permissions = dict(
            adjustments=dict(
                enabled=True,
                create=dict(
                    enabled=True,
                    max_amount=1000,
                    min_amount=0,
                    max_auto_reject=200,
                    min_auto_reject=100,
                ),
            ),
        )

        service = self.create_service_with_permissions(permissions=permissions)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 201, data)
        self.assertIsNotNone(data.get("uuid"), data)
        self.assertEqual(data.get("status"), "PENDING", data)
        self.assertEqual(Decimal(data.get("amount")), Decimal(100), data)  # type: ignore

        self.assertEqual(AdjustmentsService.list().count(), 1)

    def test_access_permission_not_pass(self):
        permissions = dict(
            adjustments=dict(
                enabled=False,  # NOT PASS
                create=dict(
                    enabled=True,
                    max_amount=1000,
                    min_amount=0,
                    max_auto_reject=200,
                    min_auto_reject=100,
                ),
            ),
        )

        service = self.create_service_with_permissions(permissions=permissions)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403, data)
        self.assertIn("Access is disabled", data["message"], data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_create_permission_not_pass(self):
        permissions = dict(
            adjustments=dict(
                enabled=True,
                create=dict(
                    enabled=False,  # NOT PASS
                    max_amount=1000,
                    min_amount=0,
                    max_auto_reject=200,
                    min_auto_reject=100,
                ),
            ),
        )

        service = self.create_service_with_permissions(permissions=permissions)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403, data)
        self.assertIn("Creating is disabled", data["message"], data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_amount_permission_not_pass(self):
        permissions = dict(
            adjustments=dict(
                enabled=True,
                create=dict(
                    enabled=True,
                    max_amount=99,  # NOT PASS
                    min_amount=0,
                    max_auto_reject=200,
                    min_auto_reject=100,
                ),
            ),
        )

        service = self.create_service_with_permissions(permissions=permissions)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403, data)
        self.assertIn("Amount is out of range", data["message"], data)
        self.assertEqual(AdjustmentsService.list().count(), 0)

    def test_auto_reject_permission_not_pass(self):
        permissions = dict(
            adjustments=dict(
                enabled=True,
                create=dict(
                    enabled=True,
                    max_amount=1000,
                    min_amount=0,
                    max_auto_reject=99,  # NOT PASS
                    min_auto_reject=98,
                ),
            ),
        )

        service = self.create_service_with_permissions(permissions=permissions)

        response = self.client.post(
            self.create_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                unit_symbol=self.unit.symbol,
                amount=100,
                description="test_description",
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403, data)
        self.assertIn("Auto reject timeout is out of range", data["message"], data)
        self.assertEqual(AdjustmentsService.list().count(), 0)
