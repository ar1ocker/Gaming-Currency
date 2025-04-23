import uuid
from typing import TYPE_CHECKING

from currencies.models import CurrencyService
from currencies.services import (
    AccountsService,
    AdjustmentsService,
    CurrencyServicesService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

if TYPE_CHECKING:
    from currencies.models import CurrencyUnit, Holder


@override_settings(ENABLE_HMAC_VALIDATION=False)
class AdjustmentRejectAPITest(TestCase):
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

        CurrencyServiceAuthTestFactory(service=service)

        return service

    def assemble_auth_headers(self, *, service: CurrencyService):
        return {settings.SERVICE_HEADER: service.name}

    def test_valid_reject_from_root(self):
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

        self.pending_transaction.refresh_from_db()
        self.assertEqual(self.pending_transaction.status, "REJECTED")

    def test_valid_reject(self):
        service = self.create_service_with_permissions(
            permissions=dict(
                adjustments=dict(
                    enabled=True,
                    reject=dict(
                        enabled=True,
                        services=[self.service.name],
                    ),
                ),
            )
        )

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.pending_transaction.uuid,
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        self.assertEqual(response.status_code, 200)

        self.pending_transaction.refresh_from_db()
        self.assertEqual(self.pending_transaction.status, "REJECTED")

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

    def test_permissions_disabled(self):
        service = self.create_service_with_permissions(
            permissions=dict(
                adjustments=dict(
                    enabled=False,  # FAIL
                ),
            )
        )

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.pending_transaction.uuid,
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertEqual("adjustments: Access is disabled", data["message"], data)

        self.pending_transaction.refresh_from_db()
        self.assertEqual(self.pending_transaction.status, "PENDING")

    def test_permissions_reject_disabled(self):
        service = self.create_service_with_permissions(
            permissions=dict(
                adjustments=dict(
                    enabled=True,
                    reject=dict(
                        enabled=False,  # FAIL
                        services=[self.service.name],
                    ),
                ),
            )
        )

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.pending_transaction.uuid,
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertEqual("adjustments: Reject is disabled", data["message"], data)

        self.pending_transaction.refresh_from_db()
        self.assertEqual(self.pending_transaction.status, "PENDING")

    def test_permissions_service_not_in_reject(self):
        service = self.create_service_with_permissions(
            permissions=dict(
                adjustments=dict(
                    enabled=True,
                    reject=dict(
                        enabled=True,
                        services=[],  # FAIL
                    ),
                ),
            )
        )

        response = self.client.post(
            self.reject_reverse_path,
            data=dict(
                uuid=self.pending_transaction.uuid,
                status_description="test_status",
            ),
            headers=self.assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertEqual("adjustments: No access to reject the transaction from another service", data["message"], data)

        self.pending_transaction.refresh_from_db()
        self.assertEqual(self.pending_transaction.status, "PENDING")
