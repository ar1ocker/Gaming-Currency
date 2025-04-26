from common.utils import assemble_auth_headers
from currencies.test_factories import CurrencyServicesTestFactory, HoldersTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(ENABLE_HMAC_VALIDATION=False)
class HoldersListAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()

        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.holders = [HoldersTestFactory() for _ in range(3)]

        cls.list_reverse_path = reverse("holders_list")

    def test_list_valid(self):
        response = self.client.get(
            self.list_reverse_path,
            data=dict(limit=100),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data.get("results")), 3, data)

    def test_list_enforce_access_permissions(self):
        service = CurrencyServicesTestFactory(permissions={})

        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.list_reverse_path,
            data=dict(limit=100),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission 'holders'", data.get("message"), data)
