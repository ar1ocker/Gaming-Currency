import hmac
from typing import Protocol

from rest_framework.request import Request
from rest_framework.validators import ValidationError


class _GeneratorProtocol(Protocol):
    def __call__(self, *, request: Request, secret_key: str) -> str: ...


class _GetterProtocol(Protocol):
    def __call__(self, *, request: Request) -> str: ...


class BaseHMACValidator:
    generator: _GeneratorProtocol
    getter: _GetterProtocol

    def validate_request(self, *, request: Request, secret_key: str):
        getted_signature = self.getter(request=request)
        generated_signature = self.generator(request=request, secret_key=secret_key)

        if not self._compare_signature(getted_signature, generated_signature):
            raise ValidationError("Request body, signature or secret key is corrupted, hmac does not match")

    def _compare_signature(self, sign_1, sign_2) -> bool:
        return hmac.compare_digest(sign_1, sign_2)
