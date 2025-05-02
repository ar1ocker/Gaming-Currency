from currencies_api.auth.base import BaseHMACValidator
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.exceptions import ValidationError


def generator(*, request, secret_key) -> str:
    return "test"


def getter(*, request) -> str:
    return "test"


def bad_getter(*, request) -> str:
    return "invalid"


class BaseHMACValidatorTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()

    def test_valid(self):
        class TestHMACValidator(BaseHMACValidator):
            generator = staticmethod(generator)
            getter = staticmethod(getter)

        request = self.factory.post("/test/")

        TestHMACValidator().validate_request(request=request, secret_key="test key")  # type: ignore

    def test_invalid(self):
        class TestHMACValidator(BaseHMACValidator):
            generator = staticmethod(generator)
            getter = staticmethod(bad_getter)

        request = self.factory.post("/test/")

        with self.assertRaisesMessage(
            ValidationError, "Request body, signature or secret key is corrupted, hmac does not match"
        ):
            TestHMACValidator().validate_request(request=request, secret_key="test key")  # type: ignore
