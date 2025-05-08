import json

from common.utils import assemble_auth_headers
from currencies.services.holders import HoldersTypeService
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    HoldersTestFactory,
    HoldersTypeTestFactory,
)
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class HoldersCreateAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.headers = assemble_auth_headers(service=cls.service)

        cls.create_reverse_path = reverse("holders_create")

    def test_create_with_only_holder_id(self):
        response = self.client.post(self.create_reverse_path, data=dict(holder_id="new_holder"), headers=self.headers)

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data.get("enabled"), True)
        self.assertEqual(data.get("holder_id"), "new_holder")
        self.assertEqual(data.get("holder_type"), HoldersTypeService.get_default().name)
        self.assertEqual(data.get("info"), {})
        self.assertEqual(data.get("created_now"), True)
        self.assertIsNotNone(data.get("created_at"))

    def test_create_with_holder_id_and_holder_type(self):
        holder_type = HoldersTypeTestFactory()

        response = self.client.post(
            self.create_reverse_path,
            data=dict(holder_id="new_holder", holder_type=holder_type.name),
            headers=self.headers,
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data.get("enabled"), True)
        self.assertEqual(data.get("holder_id"), "new_holder")
        self.assertEqual(data.get("holder_type"), holder_type.name)
        self.assertEqual(data.get("info"), {})
        self.assertEqual(data.get("created_now"), True)
        self.assertIsNotNone(data.get("created_at"))

    def test_create_with_holder_id_holder_type_and_info(self):
        holder_type = HoldersTypeTestFactory()

        info = {"test": "test"}
        response = self.client.post(
            self.create_reverse_path,
            data=dict(holder_id="new_holder", holder_type=holder_type.name, info=json.dumps(info)),
            headers=self.headers,
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data.get("enabled"), True)
        self.assertEqual(data.get("holder_id"), "new_holder")
        self.assertEqual(data.get("holder_type"), holder_type.name)
        self.assertEqual(data.get("info"), info)
        self.assertEqual(data.get("created_now"), True)
        self.assertIsNotNone(data.get("created_at"))

    def test_create_with_holder_id_and_info(self):
        info = {"test": "test"}

        response = self.client.post(
            self.create_reverse_path,
            data=dict(holder_id="new_holder", info=json.dumps(info)),
            headers=self.headers,
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data.get("enabled"), True)
        self.assertEqual(data.get("holder_id"), "new_holder")
        self.assertEqual(data.get("holder_type"), HoldersTypeService.get_default().name)
        self.assertEqual(data.get("info"), info)
        self.assertEqual(data.get("created_now"), True)
        self.assertIsNotNone(data.get("created_at"))

    def test_create_exists_not_change_holder(self):
        holder = HoldersTestFactory()

        holder_type = HoldersTypeTestFactory()

        info = {"test": "test"}
        response = self.client.post(
            self.create_reverse_path,
            data=dict(holder_id=holder.holder_id, holder_type=holder_type.name, info=json.dumps(info)),
            headers=self.headers,
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 201)
        self.assertEqual(data.get("enabled"), True)
        self.assertEqual(data.get("holder_id"), holder.holder_id)
        self.assertEqual(data.get("holder_type"), holder.holder_type.name)
        self.assertEqual(data.get("info"), {})
        self.assertEqual(data.get("created_now"), False)
        self.assertIsNotNone(data.get("created_at"))

    def test_create_enforce_create_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.post(
            self.create_reverse_path, data=dict(holder_id="new_holder"), headers=assemble_auth_headers(service=service)
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission", data.get("message"))
