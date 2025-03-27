import hmac
import re
from datetime import datetime, timedelta, timezone
from functools import wraps

from dateutil.parser import isoparse as datetime_isoparse
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request
from rest_framework.validators import ValidationError

from .models import ServiceAuth


class TimestampRequestHMACValidator:
    def __init__(
        self,
        *,
        signature_header: str,
        timestamp_header: str,
        timestamp_deviation: int,
        secret_key: str,
        hash_type: str,
    ) -> None:
        self.signature_header = signature_header
        self.timestamp_header = timestamp_header
        self.timestamp_deviation: timedelta = timedelta(seconds=timestamp_deviation)
        self.secret_key = secret_key
        self.hash_type = hash_type

    def validate_request(self, *, request: Request) -> None:
        signature_from_request = self._get_signature(request=request)

        generated_signature: str = self._generate_signature(request=request)

        if not self._compare_signature(signature_from_request, generated_signature):
            raise ValidationError("Request body, signature or secret key is corrupted, hmac does not match")

    def _get_signature(self, *, request: Request) -> str:
        if self.signature_header not in request.headers:
            raise ValidationError("HMAC header is not found")

        return request.headers[self.signature_header]

    def _get_timestamp(self, *, request: Request):
        if self.timestamp_header not in request.headers:
            raise ValidationError("Timestamp header is not found")

        return request.headers[self.timestamp_header]

    def _validate_timestamp_text(self, *, timestamp_text):
        try:
            timestamp = datetime_isoparse(timestamp_text)
        except ValueError:
            raise ValidationError("Timestamp in HMAC header have not valid format, required iso format")

        if timestamp.tzinfo is None:
            raise ValidationError("Timestamp in HMAC header must have a timezone")

        now: datetime = datetime.now(timezone.utc)

        if not (now - self.timestamp_deviation < timestamp < now + self.timestamp_deviation):
            raise ValidationError("Timestamp is very old or very far in the future")

    def _generate_signature(self, *, request: Request) -> str:
        timestamp_text = self._get_timestamp(request=request)

        self._validate_timestamp_text(timestamp_text=timestamp_text)

        body = b""
        if request.method == "GET":
            body: bytes = request.get_full_path().encode()
        else:
            body: bytes = request.body

        return hmac.digest(
            self.secret_key.encode(),
            f"{timestamp_text}.".encode() + body,
            self.hash_type,
        ).hex()

    def _compare_signature(self, sign_1, sign_2) -> bool:
        return hmac.compare_digest(sign_1, sign_2)


class BattlemetricsRequestHMACValidator:
    def __init__(
        self,
        *,
        signature_header: str,
        signature_regex: str,
        timestamp_regex: str,
        timestamp_deviation: int,
        secret_key: str,
        hash_type: str,
    ) -> None:
        self.signature_header = signature_header
        self.signature_regex = signature_regex
        self.timestamp_regex = timestamp_regex
        self.timestamp_deviation: timedelta = timedelta(seconds=timestamp_deviation)
        self.secret_key = secret_key
        self.hash_type = hash_type

    def validate_request(self, *, request: Request) -> None:
        if self.signature_header not in request.headers:
            raise ValidationError("Signature header is not found")

        signature_from_request = self._get_signature(request=request)

        generated_signature: str = self._generate_signature(request=request)

        if not self._compare_signature(signature_from_request, generated_signature):
            raise ValidationError("Request body, signature or secret key is corrupted, hmac does not match")

    def _get_signature(self, *, request: Request) -> str:
        header = request.headers[self.signature_header]

        signature_match: re.Match | None = re.search(
            self.signature_regex,
            header,
            re.A,
        )
        if signature_match is None:
            raise ValidationError("Signature not found")

        return signature_match.group(0)

    def _get_timestamp(self, *, request: Request):
        header = request.headers[self.signature_header]

        timestamp_match = re.search(self.timestamp_regex, header, flags=re.A)

        if timestamp_match is None:
            raise ValidationError("Timestamp in HMAC header not found")

        timestamp_text = timestamp_match.group(0)

        return timestamp_text

    def _validate_timestamp_text(self, *, timestamp_text):
        try:
            timestamp = datetime_isoparse(timestamp_text)
        except ValueError:
            raise ValidationError("Timestamp in HMAC header have not valid format, required iso format")

        if timestamp.tzinfo is None:
            raise ValidationError("Timestamp in HMAC header must have a timezone")

        now: datetime = datetime.now(timezone.utc)

        if not (now - self.timestamp_deviation < timestamp < now + self.timestamp_deviation):
            raise ValidationError("Timestamp is very old or very far in the future")

    def _generate_signature(self, *, request: Request) -> str:
        timestamp_text = self._get_timestamp(request=request)

        self._validate_timestamp_text(timestamp_text=timestamp_text)

        return hmac.digest(
            self.secret_key.encode(),
            f"{timestamp_text}.".encode() + request.body,
            self.hash_type,
        ).hex()

    def _compare_signature(self, sign_1, sign_2) -> bool:
        return hmac.compare_digest(sign_1, sign_2)


def hmac_service_auth(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        service_header = request.headers.get("X-SERVICE")

        if not service_header:
            raise AuthenticationFailed("Service not found")

        try:
            service = ServiceAuth.objects.get(service__name=service_header)
        except ServiceAuth.DoesNotExist:
            raise AuthenticationFailed("Service not found")

        if not service.enabled:
            raise AuthenticationFailed("Service disabled")

        if settings.ENABLE_HMAC_VALIDATION:
            validator = None
            if service.is_battlemetrics:
                validator = BattlemetricsRequestHMACValidator(
                    signature_header=settings.HMAC_SIGNATURE_HEADER,
                    signature_regex=settings.BATTLEMETRICS_SIGNATURE_REGEX,
                    timestamp_regex=settings.BATTLEMETRICS_TIMESTAMP_REGEX,
                    timestamp_deviation=settings.HMAC_TIMESTAMP_DEVIATION,
                    secret_key=service.key,
                    hash_type=settings.HMAC_HASH_TYPE,
                )
            else:
                validator = TimestampRequestHMACValidator(
                    signature_header=settings.HMAC_SIGNATURE_HEADER,
                    timestamp_header=settings.HMAC_TIMESTAMP_HEADER,
                    timestamp_deviation=settings.HMAC_TIMESTAMP_DEVIATION,
                    secret_key=service.key,
                    hash_type=settings.HMAC_HASH_TYPE,
                )

            try:
                validator.validate_request(request=request)
            except ValidationError as e:
                raise AuthenticationFailed(e.detail)

        return func(self, request, service, *args, **kwargs)

    return wrapper
