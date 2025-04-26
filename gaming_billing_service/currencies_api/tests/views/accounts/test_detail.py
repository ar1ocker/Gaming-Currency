from decimal import Decimal

from common.utils import assemble_auth_headers
from currencies.models import CheckingAccount
from currencies.services import (
    AccountsService,
    CurrencyServicesService,
    HoldersService,
    HoldersTypeService,
)
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
    HoldersTestFactory,
)
from currencies_api.models import CurrencyServiceAuth
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase


@override_settings(ENABLE_HMAC_VALIDATION=False)
class AccountDetailAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesService.get_default()
        cls.service.enabled = True
        cls.service.permissions = {"root": True}
        cls.service.save()

        cls.service_auth = CurrencyServiceAuth.objects.create(service=cls.service, key="", is_battlemetrics=False)

        cls.holder_type = HoldersTypeService.get_default()

        cls.holder = HoldersTestFactory(holder_type=cls.holder_type)
        cls.currency_unit_1 = CurrencyUnitsTestFactory()
        cls.currency_unit_2 = CurrencyUnitsTestFactory()

        cls.account_unit_1 = AccountsService.get_or_create(holder=cls.holder, currency_unit=cls.currency_unit_1)[0]

        cls.account_detail_reverse_path = reverse("checking_accounts_detail")

    def test_get_detail(self):
        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["holder_id"], self.holder.holder_id)
        self.assertEqual(data["currency_unit"], self.currency_unit_1.symbol)
        self.assertEqual(Decimal(data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in data)

    def test_get_or_create_detail(self):
        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_2.symbol,  # unit 2
                create_if_not_exists=True,
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["holder_id"], self.holder.holder_id)
        self.assertEqual(data["currency_unit"], self.currency_unit_2.symbol)
        self.assertEqual(Decimal(data["amount"]), Decimal("0.0000"))
        self.assertTrue("created_at" in data)

        self.assertEqual(CheckingAccount.objects.count(), 2)

    def test_get_with_no_access_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Missing required permission" in data["message"], data)

    def test_get_or_create_with_no_create_permissions(self):
        service = CurrencyServicesTestFactory(
            permissions=dict(
                accounts=dict(
                    enabled=True,
                    create=dict(enabled=False),
                ),
            )
        )
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id=self.holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_2.symbol,
                create_if_not_exists=True,
            ),
            headers=assemble_auth_headers(service=service),
        )

        data: dict = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertTrue("Creating is disabled" in data["message"], data)

        self.assertEqual(CheckingAccount.objects.count(), 1)

    def test_get_with_not_exists_holder(self):
        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id="not found holder",
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data.get("message"), "Holder not found")
        self.assertEqual(HoldersService.list().count(), 1)

    def test_get_with_not_exists_account(self):
        holder = HoldersTestFactory()

        response = self.client.get(
            self.account_detail_reverse_path,
            data=dict(
                holder_id=holder.holder_id,
                holder_type=self.holder_type.name,
                unit_symbol=self.currency_unit_1.symbol,
            ),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 404)
        self.assertEqual(data.get("message"), "Account not found")
