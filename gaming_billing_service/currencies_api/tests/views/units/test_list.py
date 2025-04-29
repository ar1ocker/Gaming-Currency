from common.utils import assemble_auth_headers
from currencies.test_factories import (
    CurrencyServicesTestFactory,
    CurrencyUnitsTestFactory,
)
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase
from django.urls import reverse


class UnitsListAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=cls.service)

        cls.units = [CurrencyUnitsTestFactory() for _ in range(10)]

        cls.units_list_reverse_path = reverse("currency_units_list")

    def test_valid(self):
        response = self.client.get(
            self.units_list_reverse_path,
            data=dict(limit=10),
            headers=assemble_auth_headers(service=self.service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data.get("results")), 10)

    def test_enforce_access(self):
        service = CurrencyServicesTestFactory(permissions={})
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.units_list_reverse_path,
            data=dict(limit=10),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing required permission 'units'", data.get("message"))
