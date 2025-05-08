import json

from common.utils import assemble_auth_headers
from currencies.services import HoldersService
from currencies.test_factories import CurrencyServicesTestFactory, HoldersTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class HoldersUpdateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.update_reverse_name = "holders_update"

        cls.holder = HoldersTestFactory(enabled=False, info={})

    def test_update_valid(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            reverse(self.update_reverse_name),
            data=dict(
                holder_id=self.holder.holder_id,
                enabled=True,
                info=json.dumps({"test": []}),
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200, data)

        self.assertEqual(data.get("holder_id"), self.holder.holder_id)
        self.assertTrue(data.get("enabled"))
        self.assertEqual(data.get("info"), {"test": []})

    def test_empty_holder_id(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            reverse(self.update_reverse_name),
            data=dict(
                enabled=True,
                info=json.dumps({"test": []}),
            ),
            headers=assemble_auth_headers(service=service),
        )

        self.assertEqual(response.status_code, 400)

    def test_not_exists_holder_id(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            reverse(self.update_reverse_name),
            data=dict(
                holder_id="not found",
                enabled=True,
                info=json.dumps({"test": []}),
            ),
            headers=assemble_auth_headers(service=service),
        )

        self.assertEqual(response.status_code, 404)

        self.assertEqual(HoldersService.list().count(), 1)

    def test_update_without_params(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            reverse(self.update_reverse_name),
            data=dict(
                holder_id=self.holder.holder_id,
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200, data)

        self.assertEqual(data.get("holder_id"), self.holder.holder_id)
        self.assertFalse(data.get("enabled"))
        self.assertEqual(data.get("info"), {})

    def test_update_without_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            reverse(self.update_reverse_name),
            data=dict(
                holder_id=self.holder.holder_id,
            ),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403, data)
        self.assertIn("Missing required permission", data.get("message"))
