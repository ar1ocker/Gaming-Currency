from currencies_api.auth.getters import SimpleHeaderGetter
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.validators import ValidationError


class SimpleHeaderGetterTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()
        cls.getter = SimpleHeaderGetter(header_name="test")

    def test_valid(self):
        request = self.factory.get("", headers={"test": "test header"})

        header = self.getter(request=request)  # type: ignore

        self.assertEqual(header, "test header")

    def test_header_not_found(self):
        request = self.factory.get("")

        with self.assertRaisesMessage(ValidationError, "HMAC header is not found"):
            self.getter(request=request)  # type: ignore
