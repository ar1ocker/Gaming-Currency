from django.conf import settings

from .base import BaseHMACValidator
from .generators import BattlemetricsSignatureGenerator, TimestampSignatureGenerator
from .getters import RegexHeaderGetter, SimpleHeaderGetter


class TimestampRequestHMACValidator(BaseHMACValidator):
    getter = SimpleHeaderGetter(header_name=settings.HMAC_SIGNATURE_HEADER)
    generator = TimestampSignatureGenerator(
        hash_type=settings.HMAC_HASH_TYPE,
        timestamp_header=settings.HMAC_TIMESTAMP_HEADER,
        timestamp_deviation=settings.HMAC_TIMESTAMP_DEVIATION,
    )


class BattlemetricsRequestHMACValidator(BaseHMACValidator):
    getter = RegexHeaderGetter(header_name=settings.HMAC_SIGNATURE_HEADER, regex=settings.BATTLEMETRICS_SIGNATURE_REGEX)
    generator = BattlemetricsSignatureGenerator(
        hash_type=settings.HMAC_HASH_TYPE,
        header_name=settings.HMAC_SIGNATURE_HEADER,
        timestamp_regex=settings.BATTLEMETRICS_TIMESTAMP_REGEX,
        timestamp_deviation=settings.HMAC_TIMESTAMP_DEVIATION,
    )
