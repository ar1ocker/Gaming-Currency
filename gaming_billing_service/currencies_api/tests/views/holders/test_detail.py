from common.utils import assemble_auth_headers
from currencies.test_factories import CurrencyServicesTestFactory, HoldersTestFactory
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.test import TestCase
from django.urls import reverse


class HoldersDetailAPITests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.holders = [HoldersTestFactory() for _ in range(3)]

        cls.detail_reverse_path = reverse("holders_detail")

    def test_get_valid(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.detail_reverse_path,
            data=dict(holder_id=self.holders[0].holder_id),
            headers=assemble_auth_headers(service=service),
        )

        data = response.data  # type: ignore

        self.assertEqual(response.status_code, 200)

        self.assertEqual(data.get("holder_id"), self.holders[0].holder_id)

    def test_get_not_found(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        response = self.client.get(
            self.detail_reverse_path,
            data=dict(holder_id="not founded holder id"),
            headers=assemble_auth_headers(service=service),
        )

        self.assertEqual(response.status_code, 404)
