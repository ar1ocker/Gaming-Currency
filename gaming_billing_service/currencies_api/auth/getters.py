import re

from rest_framework.request import Request
from rest_framework.validators import ValidationError


class SimpleHeaderGetter:

    def __init__(self, *, header_name) -> None:
        self.header_name = header_name

    def __call__(self, *, request: Request) -> str:
        if self.header_name not in request.headers:
            raise ValidationError("HMAC header is not found")

        return request.headers[self.header_name]


class RegexHeaderGetter:

    def __init__(self, *, header_name, regex) -> None:
        self.header_name = header_name
        self.regex = regex

    def __call__(self, *, request: Request) -> str:
        if self.header_name not in request.headers:
            raise ValidationError("HMAC header is not found")

        header = request.headers[self.header_name]

        signature_match: re.Match | None = re.search(
            self.regex,
            header,
            re.A,
        )

        if signature_match is None:
            raise ValidationError("Signature not found")

        return signature_match.group(0)
