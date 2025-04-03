from typing import TYPE_CHECKING
import uuid
from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from currencies.services import CurrencyServicesService, AccountsService, AdjustmentsService
from currencies_api.test_factories import CurrencyServiceAuthFactory
from currencies.test_factories import HoldersTestFactory, CurrencyUnitsTestFactory
from currencies.models import CurrencyService

if TYPE_CHECKING:
    from currencies.models import Holder, CurrencyUnit


class AdjustmentRejectAPITest(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesService.get_default()
        cls.service.enabled = True
        cls.service.permissions = {"root": True}
        cls.service.save()

        cls.service_auth = CurrencyServiceAuthFactory(service=cls.service)

        cls.holder: Holder = HoldersTestFactory()
        cls.unit: CurrencyUnit = CurrencyUnitsTestFactory()

        cls.account = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.unit)

        cls.pending_transaction = AdjustmentsService.create(
            service=cls.service, checking_account=cls.account, amount=100, description="test"
        )

        cls.reject_reverse_path = reverse("adjustments_reject")

    def create_service_with_permissions(self, *, permissions: dict):
        service = CurrencyService.objects.create(
            name="test_name",
            enabled=True,
            permissions=permissions,
        )

        CurrencyServiceAuthFactory(service=service)

        return service

    def assemble_auth_headers(self, *, service: CurrencyService):
        return {settings.SERVICE_HEADER: service.name}

    def test_valid_reject(self):
        service = self.create_service_with_permissions(permissions=dict(root=True))

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.pending_transaction.uuid,
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        self.assertEqual(response.status_code, 200)

    def test_uuid_not_found(self):
        service = self.create_service_with_permissions(permissions=dict(root=True))

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=uuid.uuid1(),
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 400)
        self.assertEqual("Validation error", data["message"], data)
        self.assertIn("object does not exist", str(data["extra"]["fields"]["uuid"]), data["extra"]["fields"]["uuid"])
