from decimal import Decimal

from currencies.models import CheckingAccount, Holder
from currencies.services import (
    AccountsService,
    CurrencyServicesService,
    HoldersTypeService,
)
from currencies.test_factories import CurrencyUnitsTestFactory, HoldersTestFactory
from currencies_api.models import CurrencyServiceAuth
from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase


@override_settings(ENABLE_HMAC_VALIDATION=False)
class CheckingAccountDetailTest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesService.get_default()
        cls.service.enabled = True
        cls.service.permissions = {"root": True}
        cls.service.save()

        cls.service_auth = CurrencyServiceAuth.objects.create(service=cls.service, key="", is_battlemetrics=False)

        cls.holder_type = HoldersTypeService.get_default()

        cls.holder = HoldersTestFactory.create()
        cls.currency_unit_1 = CurrencyUnitsTestFactory.create()
        cls.currency_unit_2 = CurrencyUnitsTestFactory.create()

        cls.account = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.currency_unit_1)

    def test_get_detail(self):
        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["holder_id"], self.holder.holder_id)
        self.assertEqual(data["currency_unit"], self.currency_unit_1.symbol)
        self.assertEqual(Decimal(data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in data)

    def test_get_or_create_detail(self):
        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_2.symbol,  # unit 2
                create_if_not_exists=True,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["holder_id"], self.holder.holder_id)
        self.assertEqual(data["currency_unit"], self.currency_unit_2.symbol)
        self.assertEqual(Decimal(data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in data)

        self.assertEqual(CheckingAccount.objects.count(), 2)

    def test_get_with_no_access_permissions(self):
        self.service.permissions = {}
        self.service.save()

        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Missing required permission" in data["detail"])

    def test_get_or_create_with_no_create_permissions(self):
        self.service.permissions = dict(
            accounts=dict(
                enabled=True,
                create=dict(enabled=False),
            ),
            holders=dict(
                enabled=True,
                create=dict(enabled=True),
            ),
        )
        self.service.save()

        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_2.symbol,
                create_if_not_exists=True,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Creating is disabled" in data["detail"], data)

        self.assertEqual(CheckingAccount.objects.count(), 1)

    def test_get_or_create_with_no_holders_create_permissions(self):
        self.service.permissions = dict(
            accounts=dict(
                enabled=True,
                create=dict(enabled=True),
            ),
            holders=dict(
                enabled=True,
                create=dict(enabled=False),
            ),
        )
        self.service.save()

        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_2.symbol,
                create_if_not_exists=True,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Creating is disabled" in data["detail"], data)

        self.assertEqual(CheckingAccount.objects.count(), 1)

    def test_get_or_create_with_default_holder_type(self):
        response = self.client.get(
            reverse("checking_accounts_detail"),
            data=dict(
                holder_id="new_holder_id",
                unit_symbol=self.currency_unit_2.symbol,  # unit 2
                create_if_not_exists=True,
            ),
            headers={settings.SERVICE_HEADER: self.service.name},
            content_type="application/json",
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["holder_id"], "new_holder_id")
        self.assertEqual(data["holder_type"], HoldersTypeService.get_default().name)
        self.assertEqual(data["currency_unit"], self.currency_unit_2.symbol)
        self.assertEqual(Decimal(data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in data)

        self.assertEqual(CheckingAccount.objects.count(), 2)
        self.assertEqual(Holder.objects.count(), 2)
