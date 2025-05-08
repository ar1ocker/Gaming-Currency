import hmac
from datetime import datetime, timezone

from common.utils import assemble_auth_headers
from currencies.test_factories import CurrencyServicesTestFactory
from currencies_api.auth.decorators import hmac_service_auth
from currencies_api.test_factories import CurrencyServiceAuthTestFactory
from django.conf import settings
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from rest_framework.exceptions import AuthenticationFailed


@override_settings(ENABLE_HMAC_VALIDATION=False)
class HMACServiceAuthTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()

    @hmac_service_auth
    def some_view(self, request, service_auth):
        return request, service_auth

    def test_valid(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        request = self.factory.post(
            "", headers={settings.SERVICE_HEADER: service.name}, content_type="application/json"
        )

        self.some_view(request)  # type: ignore

    def test_service_header_not_found(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        request = self.factory.post("", content_type="application/json")

        with self.assertRaisesMessage(AuthenticationFailed, "Service header not found"):
            self.some_view(request)  # type: ignore

    def test_service_not_found(self):
        service = CurrencyServicesTestFactory()
        CurrencyServiceAuthTestFactory(service=service)

        request = self.factory.post("", headers={settings.SERVICE_HEADER: "notfound"}, content_type="application/json")

        with self.assertRaisesMessage(AuthenticationFailed, "Service not found"):
            self.some_view(request)  # type: ignore

    def test_service_disabled(self):
        service = CurrencyServicesTestFactory(enabled=False)
        CurrencyServiceAuthTestFactory(service=service)

        request = self.factory.post(
            "", headers={settings.SERVICE_HEADER: service.name}, content_type="application/json"
        )

        with self.assertRaisesMessage(AuthenticationFailed, "Service disabled"):
            self.some_view(request)  # type: ignore


@override_settings(ENABLE_HMAC_VALIDATION=True)
class HMACServiceAuthWithEnabledValidationTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.factory = RequestFactory()

    @hmac_service_auth
    def some_view(self, request, service_auth):
        return request, service_auth

    def test_timestamp_hmac_validation_valid(self):
        service = CurrencyServicesTestFactory()
        service_auth = CurrencyServiceAuthTestFactory(service=service, is_battlemetrics=False)

        timestamp_text = datetime.now(timezone.utc).isoformat()

        signature = hmac.digest(
            service_auth.key.encode(), f"{timestamp_text}./.{{}}".encode(), settings.HMAC_HASH_TYPE
        ).hex()

        request = self.factory.post(
            "",
            headers=assemble_auth_headers(
                service=service,
                additional_headers={
                    settings.HMAC_TIMESTAMP_HEADER: timestamp_text,
                    settings.HMAC_SIGNATURE_HEADER: signature,
                },
            ),
            content_type="application/json",
        )

        self.some_view(request=request)  # type: ignore

    def test_battlemetrics_hmac_validation_valid(self):
        service = CurrencyServicesTestFactory()
        service_auth = CurrencyServiceAuthTestFactory(is_battlemetrics=True, service=service)

        timestamp_text = datetime.now(timezone.utc).isoformat()

        signature = hmac.digest(
            service_auth.key.encode(), f"{timestamp_text}.{{}}".encode(), settings.HMAC_HASH_TYPE
        ).hex()

        request = self.factory.post(
            "",
            headers=assemble_auth_headers(
                service=service,
                additional_headers={
                    settings.HMAC_SIGNATURE_HEADER: f"t={timestamp_text},s={signature}",
                },
            ),
            content_type="application/json",
        )

        self.some_view(request=request)  # type: ignore
