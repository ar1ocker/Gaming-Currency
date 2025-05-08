import hmac
import re
from datetime import datetime, timedelta, timezone

from dateutil.parser import isoparse as datetime_isoparse
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request


class TimestampSignatureGenerator:
    def __init__(self, *, hash_type, timestamp_header, timestamp_deviation: timedelta):
        self.hash_type = hash_type
        self.timestamp_header = timestamp_header
        self.timestamp_deviation = timestamp_deviation

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

    def __call__(self, *, request: Request, secret_key: str) -> str:
        timestamp_text = self._get_timestamp(request=request)

        self._validate_timestamp_text(timestamp_text=timestamp_text)

        path = request.get_full_path()

        body: bytes = request.body

        return hmac.digest(
            secret_key.encode(),
            f"{timestamp_text}.{path}.".encode() + body,
            self.hash_type,
        ).hex()


class BattlemetricsSignatureGenerator:
    def __init__(self, *, hash_type: str, header_name: str, timestamp_regex: str, timestamp_deviation: timedelta):
        self.hash_type = hash_type
        self.header_name = header_name
        self.timestamp_regex = timestamp_regex
        self.timestamp_deviation = timestamp_deviation

    def _get_timestamp(self, *, request: Request):
        if self.header_name not in request.headers:
            raise ValidationError("HMAC header is not found")

        header = request.headers[self.header_name]

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

    def __call__(self, *, request: Request, secret_key: str) -> str:
        timestamp_text = self._get_timestamp(request=request)

        self._validate_timestamp_text(timestamp_text=timestamp_text)

        return hmac.digest(
            secret_key.encode(),
            f"{timestamp_text}.".encode() + request.body,
            self.hash_type,
        ).hex()
