import hmac
from datetime import datetime, timedelta, timezone

from currencies_api.auth.generators import BattlemetricsSignatureGenerator
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.exceptions import ValidationError


class BattlemetricsSignatureGeneratorTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.generator = BattlemetricsSignatureGenerator(
            hash_type="sha256",
            header_name="test",
            timestamp_regex=r"(?<=t=).*",
            timestamp_deviation=timedelta(seconds=10),
        )

        cls.secret_key = "secret key"

        cls.factory = RequestFactory()

    def test_valid(self):
        timestamp_text = datetime.now(timezone.utc).isoformat()

        valid_signature = hmac.digest(
            self.secret_key.encode(), f'{timestamp_text}.{{"query": "random"}}'.encode(), "sha256"
        ).hex()

        request = self.factory.post(
            "/path/to/view/",
            data={"query": "random"},
            headers={"test": f"t={timestamp_text}"},
            content_type="application/json",
        )

        self.assertEqual(self.generator(request=request, secret_key=self.secret_key), valid_signature)  # type: ignore

    def test_header_not_found(self):
        request = self.factory.post("/path/to/view/", data={"query": "random"}, content_type="application/json")

        with self.assertRaisesMessage(ValidationError, "HMAC header is not found"):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore

    def test_timestamp_in_header_not_found(self):
        request = self.factory.post(
            "/path/to/view/", data={"query": "random"}, headers={"test": "random"}, content_type="application/json"
        )

        with self.assertRaisesMessage(ValidationError, "Timestamp in HMAC header not found"):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore

    def test_timestamp_is_not_valid(self):
        request = self.factory.post(
            "/path/to/view/",
            data={"query": "random"},
            headers={"test": "t=notValidTIMESTAMP"},
            content_type="application/json",
        )

        with self.assertRaisesMessage(
            ValidationError, "Timestamp in HMAC header have not valid format, required iso format"
        ):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore

    def test_timestamp_without_timezone(self):
        timestamp_text = datetime.now().isoformat()

        request = self.factory.post(
            "/path/to/view/",
            data={"query": "random"},
            headers={"test": f"t={timestamp_text}"},
            content_type="application/json",
        )

        with self.assertRaisesMessage(ValidationError, "Timestamp in HMAC header must have a timezone"):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore

    def test_timestamp_is_old(self):
        timestamp_text = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

        request = self.factory.get("/path/to/view/", data={"query": "random"}, headers={"test": f"t={timestamp_text}"})

        with self.assertRaisesMessage(ValidationError, "Timestamp is very old or very far in the future"):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore

    def test_timestamp_is_in_future(self):
        timestamp_text = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()

        request = self.factory.get("/path/to/view/", data={"query": "random"}, headers={"test": f"t={timestamp_text}"})

        with self.assertRaisesMessage(ValidationError, "Timestamp is very old or very far in the future"):
            self.generator(request=request, secret_key=self.secret_key)  # type: ignore
