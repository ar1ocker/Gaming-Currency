import hmac
from typing import Callable

from rest_framework.request import Request
from rest_framework.validators import ValidationError


class BaseHMACValidator:
    signature_generator: Callable
    signature_getter: Callable

    def validate_request(self, *, request: Request, secret_key: str):
        getted_signature = self.signature_getter(request=request)
        generated_signature = self.signature_generator(request=request, secret_key=secret_key)

        if not self._compare_signature(getted_signature, generated_signature):
            raise ValidationError("Request body, signature or secret key is corrupted, hmac does not match")

    def _compare_signature(self, sign_1, sign_2) -> bool:
        return hmac.compare_digest(sign_1, sign_2)
