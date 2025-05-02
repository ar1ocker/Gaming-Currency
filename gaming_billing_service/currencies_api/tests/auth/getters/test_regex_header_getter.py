from currencies_api.auth.getters import RegexHeaderGetter
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.exceptions import ValidationError


class RegexHeaderGetterTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()
        cls.getter = RegexHeaderGetter(header_name="test", regex=r"(?<=test )(.+)")

    def test_valid(self):
        request = self.factory.get("", headers={"test": "test header"})

        header = self.getter(request=request)  # type: ignore

        self.assertEqual(header, "header")

    def test_header_not_found(self):
        request = self.factory.get("")

        with self.assertRaisesMessage(ValidationError, "HMAC header is not found"):
            self.getter(request=request)  # type: ignore

    def test_signature_not_found(self):
        request = self.factory.get("", headers={"test": "header"})

        with self.assertRaisesMessage(ValidationError, "Signature not found"):
            self.getter(request=request)  # type: ignore
