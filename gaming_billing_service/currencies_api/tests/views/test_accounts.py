from decimal import Decimal

from currencies.models import CheckingAccount, CurrencyUnit
from currencies.services import (
    AccountsService,
    CurrencyServicesService,
    HoldersService,
    HoldersTypeService,
)
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

        cls.holder = HoldersService.get_or_create(holder_id="test", holder_type=cls.holder_type)
        cls.currency_unit_1 = CurrencyUnit.objects.create(symbol="ppg", measurement="popugai")
        cls.currency_unit_2 = CurrencyUnit.objects.create(symbol="ppg2", measurement="abrakadabra")

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

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["holder_id"], self.holder.holder_id)
        self.assertEqual(response.data["currency_unit"], self.currency_unit_1.symbol)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in response.data)

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

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["holder_id"], self.holder.holder_id)
        self.assertEqual(response.data["currency_unit"], self.currency_unit_2.symbol)
        self.assertEqual(Decimal(response.data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in response.data)
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

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Missing required permission" in response.data["detail"])

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

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Creating is disabled" in response.data["detail"], response.data)

        self.assertEqual(CheckingAccount.objects.count(), 1)
