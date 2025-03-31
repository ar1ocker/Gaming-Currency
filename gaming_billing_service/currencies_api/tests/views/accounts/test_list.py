from currencies.models import CurrencyUnit
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
class CheckingAccountListTest(APITestCase):
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

    def test_list(self):
        response = self.client.get(
            reverse("checking_accounts_list"), data=dict(limit=1), headers={settings.SERVICE_HEADER: self.service.name}
        )
        data = response.data  # type: ignore

        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["holder_id"], "test")

    def test_list_many(self):
        AccountsService.get_or_create(holder=self.holder, currency_unit=self.currency_unit_2)

        response = self.client.get(
            reverse("checking_accounts_list"), data=dict(limit=3), headers={settings.SERVICE_HEADER: self.service.name}
        )

        data = response.data  # type: ignore

        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(data["results"][0]["holder_id"], "test")

    def test_list_without_permissions(self):
        self.service.permissions = dict(
            accounts=dict(
                enabled=False,
            ),
        )
        self.service.save()

        response = self.client.get(
            reverse("checking_accounts_list"), data=dict(limit=1), headers={settings.SERVICE_HEADER: self.service.name}
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Access is disabled" in data["detail"], data)
