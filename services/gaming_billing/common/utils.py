import logging
from decimal import Decimal
from functools import wraps

from currencies.models import CurrencyService
from django.conf import settings
from django.db import OperationalError

logger = logging.getLogger(__name__)


def retry_on_serialization_error(max_retries=3):
    """
    Декоратор для повторения вызова функции в случае ошибок сериализации.

    :param max_retries: Максимальное количество попыток.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except OperationalError as e:
                    # Проверяем, является ли ошибка ошибкой сериализации
                    if "serialization" in str(e).lower() or "could not serialize" in str(e).lower():
                        retries += 1
                        logger.warning(f"Ошибка сериализации (попытка {retries} из {max_retries}): {e}")
                        if retries >= max_retries:
                            logger.error("Достигнуто максимальное количество попыток сериализации.")
                            raise
                    else:
                        # Если это не ошибка сериализации, пробрасываем исключение дальше
                        raise

        return wrapper

    return decorator


def format_decimal(decimal_value: Decimal) -> str:
    formatted_text = format(decimal_value, "f")
    if "." in formatted_text:
        formatted_text = formatted_text.rstrip("0").rstrip(".")
    return formatted_text


def get_decimal_places(decimal: Decimal) -> int:
    places: int = decimal.normalize().as_tuple().exponent  # type: ignore

    if places > 0:
        return 0

    return abs(places)


def assemble_auth_headers(*, service: CurrencyService, additional_headers: dict | None = None):
    headers = {settings.SERVICE_HEADER: service.name}

    if additional_headers is not None:
        return headers | additional_headers

    return headers
